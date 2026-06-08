'use client'
import { useEffect, useState, useCallback } from 'react'
import {
  DndContext, DragOverlay, PointerSensor, useSensor, useSensors,
  type DragStartEvent, type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useDroppable } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { crmApi, type ClientCard, type KanbanColumn } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Search, GripVertical } from 'lucide-react'

const STAGE_COLORS: Record<string, string> = {
  nuevo: 'bg-slate-500',
  contactado: 'bg-blue-500',
  calificado: 'bg-yellow-500',
  propuesta: 'bg-orange-500',
  negociacion: 'bg-purple-500',
  cerrado_ganado: 'bg-green-500',
  cerrado_perdido: 'bg-red-500',
}

function ClientCardItem({ client }: { client: ClientCard }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: client.id })
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1 }

  return (
    <div ref={setNodeRef} style={style} className="bg-card border border-border rounded-md p-3 space-y-1.5 cursor-default">
      <div className="flex items-center gap-2">
        <GripVertical className="w-3 h-3 text-muted-foreground cursor-grab" {...attributes} {...listeners} />
        <span className="text-sm font-medium text-foreground truncate">{client.full_name}</span>
      </div>
      {client.email && <p className="text-xs text-muted-foreground truncate">{client.email}</p>}
      <div className="flex items-center justify-between">
        <Badge variant="outline" className="text-xs">{client.source}</Badge>
        {client.lead_score !== null && (
          <span className="text-xs text-muted-foreground">Score: {Math.round((client.lead_score ?? 0) * 100)}%</span>
        )}
      </div>
    </div>
  )
}

function KanbanCol({ column }: { column: KanbanColumn }) {
  const { setNodeRef, isOver } = useDroppable({ id: column.stage })

  return (
    <div className="flex flex-col w-60 flex-shrink-0">
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-2.5 h-2.5 rounded-full ${STAGE_COLORS[column.stage] ?? 'bg-gray-400'}`} />
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{column.stage.replace('_', ' ')}</h3>
        <span className="ml-auto text-xs text-muted-foreground">{column.clients.length}</span>
      </div>
      <div
        ref={setNodeRef}
        className={`flex-1 min-h-[200px] space-y-2 rounded-lg p-2 transition-colors ${isOver ? 'bg-accent' : 'bg-muted/30'}`}
      >
        <SortableContext items={column.clients.map((c) => c.id)} strategy={verticalListSortingStrategy}>
          {column.clients.map((client) => (
            <ClientCardItem key={client.id} client={client} />
          ))}
        </SortableContext>
      </div>
    </div>
  )
}

export default function CRMPage() {
  const [columns, setColumns] = useState<KanbanColumn[]>([])
  const [activeClient, setActiveClient] = useState<ClientCard | null>(null)
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState<ClientCard[] | null>(null)

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))

  useEffect(() => {
    crmApi.kanban().then((r) => setColumns(r.data)).catch(() => {})
  }, [])

  const handleSearch = useCallback(async (q: string) => {
    setSearch(q)
    if (!q.trim()) { setSearchResults(null); return }
    try {
      const res = await crmApi.search(q)
      setSearchResults(res.data)
    } catch { setSearchResults([]) }
  }, [])

  const handleDragStart = (e: DragStartEvent) => {
    const client = columns.flatMap((c) => c.clients).find((c) => c.id === e.active.id)
    setActiveClient(client ?? null)
  }

  const handleDragEnd = async (e: DragEndEvent) => {
    const { active, over } = e
    setActiveClient(null)
    if (!over || active.id === over.id) return

    const targetStage = columns.find((c) => c.stage === over.id)?.stage
      ?? columns.find((c) => c.clients.some((cl) => cl.id === over.id))?.stage
    if (!targetStage) return

    const clientId = active.id as string
    setColumns((prev) => prev.map((col) => ({
      ...col,
      clients: col.stage === targetStage
        ? col.clients.find((c) => c.id === clientId)
          ? col.clients
          : [...col.clients, prev.flatMap((c) => c.clients).find((c) => c.id === clientId)!]
        : col.clients.filter((c) => c.id !== clientId),
    })))

    try {
      await crmApi.updateStage(clientId, targetStage)
    } catch {
      crmApi.kanban().then((r) => setColumns(r.data)).catch(() => {})
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">CRM — Kanban</h1>
          <p className="text-sm text-muted-foreground">Arrastrá los leads entre etapas</p>
        </div>
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Buscar clientes..."
            className="pl-9"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>
      </div>

      {searchResults ? (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">{searchResults.length} resultado(s)</p>
          {searchResults.map((c) => (
            <Card key={c.id}>
              <CardContent className="py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{c.full_name}</p>
                  <p className="text-xs text-muted-foreground">{c.email ?? c.phone}</p>
                </div>
                <Badge>{c.lead_stage}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          <div className="flex gap-4 overflow-x-auto pb-4">
            {columns.map((col) => <KanbanCol key={col.stage} column={col} />)}
          </div>
          <DragOverlay>
            {activeClient && (
              <div className="bg-card border border-primary rounded-md p-3 shadow-xl w-56">
                <p className="text-sm font-medium">{activeClient.full_name}</p>
              </div>
            )}
          </DragOverlay>
        </DndContext>
      )}
    </div>
  )
}
