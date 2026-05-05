import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { fetchGraph, GraphData } from '../api'
import { useState } from 'react'

interface Props {
  employeeId?: string
  height?: number
}

export default function GraphCanvas({ employeeId, height = 500 }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchGraph(employeeId)
      .then(setData)
      .catch((e) => setError('Graph unavailable'))
  }, [employeeId])

  useEffect(() => {
    if (!svgRef.current || data.nodes.length === 0) return
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = svgRef.current.clientWidth || 600

    const simulation = d3
      .forceSimulation(data.nodes as any)
      .force('link', d3.forceLink(data.links as any).id((d: any) => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(20))

    const g = svg.append('g')

    // Zoom
    svg.call(
      d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.2, 4]).on('zoom', (e) => {
        g.attr('transform', e.transform)
      })
    )

    // Links
    const link = g
      .append('g')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('stroke', '#334155')
      .attr('stroke-width', (d) => Math.sqrt(d.weight) * 0.8)

    // Nodes
    const node = g
      .append('g')
      .selectAll('circle')
      .data(data.nodes)
      .join('circle')
      .attr('r', (d) => (d.type === 'employee' ? 8 : 5))
      .attr('fill', (d) => {
        if (d.type === 'system') return '#475569'
        if (d.flagged) return '#ef4444'
        const score = d.risk_score || 0
        if (score >= 0.9) return '#ef4444'
        if (score >= 0.7) return '#f97316'
        if (score >= 0.5) return '#eab308'
        return '#3b82f6'
      })
      .attr('stroke', '#1e293b')
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .call(
        d3.drag<SVGCircleElement, any>()
          .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
          .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y })
          .on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null })
      )

    // Labels
    const label = g
      .append('g')
      .selectAll('text')
      .data(data.nodes.filter((d) => d.type === 'employee'))
      .join('text')
      .text((d) => d.id.slice(-6))
      .attr('font-size', '9px')
      .attr('fill', '#94a3b8')
      .attr('dy', -12)
      .attr('text-anchor', 'middle')

    // Tooltip
    const tooltip = d3
      .select('body')
      .append('div')
      .attr('class', 'fixed z-50 bg-card border border-border rounded px-2 py-1 text-xs pointer-events-none hidden')

    node
      .on('mouseover', (e, d) => {
        tooltip
          .classed('hidden', false)
          .html(`<strong>${d.id}</strong><br/>type: ${d.type}${d.risk_score != null ? `<br/>score: ${d.risk_score.toFixed(3)}` : ''}`)
          .style('left', (e.pageX + 10) + 'px')
          .style('top', (e.pageY - 20) + 'px')
      })
      .on('mousemove', (e) => {
        tooltip.style('left', (e.pageX + 10) + 'px').style('top', (e.pageY - 20) + 'px')
      })
      .on('mouseout', () => { tooltip.classed('hidden', true) })

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y)
      node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y)
      label.attr('x', (d: any) => d.x).attr('y', (d: any) => d.y)
    })

    return () => {
      simulation.stop()
      tooltip.remove()
    }
  }, [data, height])

  return (
    <div className="w-full h-full flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="font-semibold text-sm text-foreground">
          {employeeId ? `Topology: ${employeeId}` : 'Risk Topology (Top 50)'}
        </h2>
        <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
          <span><span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />Critical</span>
          <span><span className="inline-block w-2 h-2 rounded-full bg-orange-500 mr-1" />High</span>
          <span><span className="inline-block w-2 h-2 rounded-full bg-yellow-500 mr-1" />Medium</span>
          <span><span className="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1" />Normal</span>
          <span><span className="inline-block w-2 h-2 rounded-full bg-slate-500 mr-1" />System</span>
        </div>
      </div>
      {error ? (
        <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">{error}</div>
      ) : data.nodes.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
          Graph will populate as events are processed…
        </div>
      ) : (
        <svg ref={svgRef} className="w-full flex-1" style={{ height }} />
      )}
    </div>
  )
}
