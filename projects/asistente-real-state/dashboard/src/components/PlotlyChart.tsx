'use client'
import dynamic from 'next/dynamic'
import { useTheme } from 'next-themes'

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false })

interface PlotlyChartProps {
  figure: { data: object[]; layout: object }
  className?: string
}

export function PlotlyChart({ figure, className }: PlotlyChartProps) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const layout = {
    ...figure.layout,
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: isDark ? '#e2e8f0' : '#1e293b', size: 12 },
    xaxis: {
      ...((figure.layout as Record<string, unknown>).xaxis as object ?? {}),
      gridcolor: isDark ? '#1e293b' : '#e2e8f0',
    },
    yaxis: {
      ...((figure.layout as Record<string, unknown>).yaxis as object ?? {}),
      gridcolor: isDark ? '#1e293b' : '#e2e8f0',
    },
    margin: { l: 40, r: 20, t: 40, b: 40 },
  }

  return (
    <Plot
      data={figure.data as Plotly.Data[]}
      layout={layout as Partial<Plotly.Layout>}
      config={{ displayModeBar: false, responsive: true }}
      className={className}
      style={{ width: '100%', height: '100%' }}
    />
  )
}
