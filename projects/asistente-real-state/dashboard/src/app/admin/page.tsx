'use client'
import { useEffect, useState } from 'react'
import { scrapingApi, ragApi, predictionsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Play, RefreshCw, Trash2, Brain, Database } from 'lucide-react'
import { toast } from '@/hooks/use-toast'

interface ScrapingSource {
  id: string
  name: string
  source_type: string
  is_active: boolean
  last_run_at: string | null
  last_run_status: string | null
}

interface RagDoc {
  id: string
  title: string
  chunk_count: number
  created_at: string
}

export default function AdminPage() {
  const [sources, setSources] = useState<ScrapingSource[]>([])
  const [ragDocs, setRagDocs] = useState<RagDoc[]>([])
  const [trainStatus, setTrainStatus] = useState<string | null>(null)

  useEffect(() => {
    scrapingApi.listSources().then((r) => setSources(r.data)).catch(() => {})
    ragApi.list().then((r) => setRagDocs(r.data)).catch(() => {})
  }, [])

  const runSource = async (id: string) => {
    try {
      await scrapingApi.runSource(id)
      toast({ title: 'Scraping encolado', description: 'El job fue enviado al worker.' })
      setSources((prev) => prev.map((s) => s.id === id ? { ...s, last_run_status: 'queued' } : s))
    } catch {
      toast({ title: 'Error', description: 'No se pudo encolar el job.', variant: 'destructive' })
    }
  }

  const resetCB = async (id: string) => {
    try {
      await scrapingApi.resetCircuitBreaker(id)
      toast({ title: 'Circuit breaker reseteado' })
    } catch {
      toast({ title: 'Error', variant: 'destructive' })
    }
  }

  const deleteRagDoc = async (id: string) => {
    try {
      await ragApi.delete(id)
      setRagDocs((prev) => prev.filter((d) => d.id !== id))
      toast({ title: 'Documento eliminado' })
    } catch {
      toast({ title: 'Error al eliminar', variant: 'destructive' })
    }
  }

  const triggerTrain = async () => {
    setTrainStatus('training')
    try {
      await predictionsApi.train()
      setTrainStatus('done')
      toast({ title: 'Entrenamiento iniciado', description: 'El modelo XGBoost se está reentrenando.' })
    } catch {
      setTrainStatus('error')
      toast({ title: 'Error en entrenamiento', variant: 'destructive' })
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Admin Panel</h1>
        <p className="text-sm text-muted-foreground">Gestión de scraping, RAG y modelos ML</p>
      </div>

      <Tabs defaultValue="scraping">
        <TabsList>
          <TabsTrigger value="scraping">Scraping</TabsTrigger>
          <TabsTrigger value="rag">RAG / Documentos</TabsTrigger>
          <TabsTrigger value="ml">ML / Scoring</TabsTrigger>
        </TabsList>

        <TabsContent value="scraping" className="space-y-3">
          {sources.length === 0 && (
            <p className="text-sm text-muted-foreground py-4 text-center">No hay fuentes configuradas.</p>
          )}
          {sources.map((s) => (
            <Card key={s.id}>
              <CardContent className="py-4 flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{s.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className="text-xs">{s.source_type}</Badge>
                    <Badge variant={s.is_active ? 'default' : 'secondary'} className="text-xs">
                      {s.is_active ? 'activo' : 'inactivo'}
                    </Badge>
                    {s.last_run_status && (
                      <span className="text-xs text-muted-foreground">Status: {s.last_run_status}</span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => runSource(s.id)} disabled={!s.is_active}>
                    <Play className="w-3 h-3 mr-1" /> Run
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => resetCB(s.id)}>
                    <RefreshCw className="w-3 h-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="rag" className="space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-4 h-4 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">{ragDocs.length} documento(s) indexado(s)</p>
          </div>
          {ragDocs.map((d) => (
            <Card key={d.id}>
              <CardContent className="py-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{d.title}</p>
                  <p className="text-xs text-muted-foreground">{d.chunk_count} chunks — {new Date(d.created_at).toLocaleDateString('es-AR')}</p>
                </div>
                <Button size="sm" variant="ghost" onClick={() => deleteRagDoc(d.id)}>
                  <Trash2 className="w-4 h-4 text-destructive" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="ml">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Brain className="w-4 h-4" /> XGBoost Lead Scorer
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Reentrenar el modelo con los datos actuales de clientes e interacciones.
                Requiere mínimo 50 muestras de entrenamiento.
              </p>
              <Button onClick={triggerTrain} disabled={trainStatus === 'training'}>
                {trainStatus === 'training' ? 'Entrenando...' : 'Reentrenar modelo'}
              </Button>
              {trainStatus === 'done' && <p className="text-sm text-green-600">Entrenamiento iniciado correctamente.</p>}
              {trainStatus === 'error' && <p className="text-sm text-destructive">Error al iniciar entrenamiento.</p>}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
