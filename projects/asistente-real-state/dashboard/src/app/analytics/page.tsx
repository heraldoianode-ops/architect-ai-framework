'use client'
import { useEffect, useState } from 'react'
import { analyticsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PlotlyChart } from '@/components/PlotlyChart'

type Figure = { data: object[]; layout: object }

export default function AnalyticsPage() {
  const [funnel, setFunnel] = useState<Figure | null>(null)
  const [activity, setActivity] = useState<Figure | null>(null)
  const [agents, setAgents] = useState<Figure | null>(null)
  const [days, setDays] = useState('30')

  useEffect(() => {
    analyticsApi.funnel().then((r) => setFunnel(r.data)).catch(() => {})
    analyticsApi.agents().then((r) => setAgents(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    analyticsApi.activity(Number(days)).then((r) => setActivity(r.data)).catch(() => {})
  }, [days])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-sm text-muted-foreground">Métricas del ecosistema inmobiliario</p>
      </div>

      <Tabs defaultValue="leads">
        <TabsList>
          <TabsTrigger value="leads">Funnel de leads</TabsTrigger>
          <TabsTrigger value="activity">Actividad</TabsTrigger>
          <TabsTrigger value="agents">Agentes</TabsTrigger>
        </TabsList>

        <TabsContent value="leads">
          <Card>
            <CardHeader><CardTitle className="text-sm">Distribución por etapa</CardTitle></CardHeader>
            <CardContent className="h-80">
              {funnel ? <PlotlyChart figure={funnel} className="h-full" /> : <p className="text-sm text-muted-foreground text-center pt-20">Cargando...</p>}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-sm">Interacciones en el tiempo</CardTitle>
              <Select value={days} onValueChange={setDays}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">7 días</SelectItem>
                  <SelectItem value="30">30 días</SelectItem>
                  <SelectItem value="90">90 días</SelectItem>
                </SelectContent>
              </Select>
            </CardHeader>
            <CardContent className="h-80">
              {activity ? <PlotlyChart figure={activity} className="h-full" /> : <p className="text-sm text-muted-foreground text-center pt-20">Cargando...</p>}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agents">
          <Card>
            <CardHeader><CardTitle className="text-sm">Performance por agente</CardTitle></CardHeader>
            <CardContent className="h-80">
              {agents ? <PlotlyChart figure={agents} className="h-full" /> : <p className="text-sm text-muted-foreground text-center pt-20">Cargando...</p>}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
