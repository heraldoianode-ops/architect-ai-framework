'use client'
import { useEffect, useState } from 'react'
import { analyticsApi, type SummaryKPIs } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PlotlyChart } from '@/components/PlotlyChart'
import { Users, TrendingUp, Building2, MessageSquare, CheckCircle } from 'lucide-react'

const KPI_CONFIG = [
  { key: 'total_clients', label: 'Clientes totales', icon: Users, color: 'text-blue-500' },
  { key: 'hot_leads', label: 'Leads calientes', icon: TrendingUp, color: 'text-red-500' },
  { key: 'total_properties', label: 'Propiedades', icon: Building2, color: 'text-green-500' },
  { key: 'interactions_this_week', label: 'Interacciones sem.', icon: MessageSquare, color: 'text-yellow-500' },
  { key: 'closed_this_month', label: 'Cierres mes', icon: CheckCircle, color: 'text-purple-500' },
] as const

export default function HomePage() {
  const [kpis, setKpis] = useState<SummaryKPIs | null>(null)
  const [funnel, setFunnel] = useState<{ data: object[]; layout: object } | null>(null)
  const [activity, setActivity] = useState<{ data: object[]; layout: object } | null>(null)
  const [forecast, setForecast] = useState<{ data: object[]; layout: object } | null>(null)

  useEffect(() => {
    analyticsApi.summary().then((r) => setKpis(r.data)).catch(() => {})
    analyticsApi.funnel().then((r) => setFunnel(r.data)).catch(() => {})
    analyticsApi.activity().then((r) => setActivity(r.data)).catch(() => {})
    analyticsApi.forecast().then((r) => setForecast(r.data)).catch(() => {})
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Resumen operacional en tiempo real</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {KPI_CONFIG.map(({ key, label, icon: Icon, color }) => (
          <Card key={key}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-medium text-muted-foreground">{label}</CardTitle>
                <Icon className={`w-4 h-4 ${color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {kpis ? kpis[key as keyof SummaryKPIs] : '—'}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-sm">Funnel de leads</CardTitle></CardHeader>
          <CardContent className="h-64">
            {funnel ? <PlotlyChart figure={funnel} className="h-full" /> : <div className="h-full flex items-center justify-center text-muted-foreground text-sm">Cargando...</div>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm">Actividad (30d)</CardTitle></CardHeader>
          <CardContent className="h-64">
            {activity ? <PlotlyChart figure={activity} className="h-full" /> : <div className="h-full flex items-center justify-center text-muted-foreground text-sm">Cargando...</div>}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-sm">Forecast de cierres</CardTitle></CardHeader>
        <CardContent className="h-64">
          {forecast ? <PlotlyChart figure={forecast} className="h-full" /> : <div className="h-full flex items-center justify-center text-muted-foreground text-sm">Cargando...</div>}
        </CardContent>
      </Card>
    </div>
  )
}
