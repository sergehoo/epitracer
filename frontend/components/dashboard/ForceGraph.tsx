'use client';

/**
 * ForceGraph — graphe D3 force-directed unifié, optimisé pour grands volumes.
 *
 * Optimisations clés :
 *   - alphaDecay/velocityDecay rapides → convergence en ~2 s
 *   - charge / collision / link distance qui scalent avec N
 *   - labels conditionnels (cachés si trop de nœuds)
 *   - pré-positionnement des hubs en cercle pour démarrer proprement
 *   - prop "frozen" : fige tous les nœuds (drag instantané, zéro tick)
 *   - opacité 0.1 pour les nœuds non-matchés (statusFilter)
 */
import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useRouter } from 'next/navigation';

export type ClusterType = 'flight' | 'phone' | 'origin' | 'companion' | 'residence';

export interface Member {
  public_id: string;
  full_name: string;
  status: string;
  risk_level: string | null;
  risk_score: number | null;
  phone: string | null;
  emergency_phone: string | null;
  flight: string | null;
  seat_number: string | null;
  arrival_date: string | null;
  entry_point: string | null;
  nationality: string | null;
  hotel: string | null;
  commune: string | null;
  room_number: string | null;
}

export interface CompanionPair { a: string; b: string; relationship: string }

export interface ClusterShape {
  type: ClusterType;
  key: string;
  label: string;
  size: number;
  members: Member[];
  pairs?: CompanionPair[];
}

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  kind: 'hub' | 'traveler';
  label: string;
  clusterType?: ClusterType;
  status?: string;
  member?: Member;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  label: string;
  clusterType: ClusterType;
}

const STATUS_COLOR: Record<string, string> = {
  cleared:    '#10B981',
  monitoring: '#0EA5E9',
  quarantine: '#F59E0B',
  suspect:    '#EF4444',
  confirmed:  '#7F1D1D',
  recovered:  '#6366F1',
  deceased:   '#111827',
};

const TYPE_COLOR: Record<ClusterType, string> = {
  flight:    '#F77F00',
  phone:     '#0EA5E9',
  origin:    '#D4A017',
  companion: '#EF4444',
  residence: '#009B5A',
};

/* ============================================================
   Construction du graphe fusionné
   ============================================================ */
function buildMergedGraph(clusters: ClusterShape[]): { nodes: GraphNode[]; links: GraphLink[] } {
  const nodeMap = new Map<string, GraphNode>();
  const links: GraphLink[] = [];
  const linkSeen = new Set<string>();

  const addTraveler = (m: Member) => {
    if (!nodeMap.has(m.public_id)) {
      nodeMap.set(m.public_id, {
        id: m.public_id,
        kind: 'traveler',
        label: m.full_name,
        status: m.status,
        member: m,
      });
    }
  };

  clusters.forEach((cluster) => {
    cluster.members.forEach(addTraveler);

    if (cluster.type === 'companion') {
      (cluster.pairs || []).forEach((p) => {
        const key = `comp:${[p.a, p.b].sort().join('|')}`;
        if (linkSeen.has(key)) return;
        linkSeen.add(key);
        links.push({
          source: p.a, target: p.b,
          label: p.relationship || 'Cas-contact',
          clusterType: 'companion',
        });
      });
      return;
    }

    const hubId = `__hub__${cluster.key}`;
    nodeMap.set(hubId, {
      id: hubId, kind: 'hub',
      label: cluster.label, clusterType: cluster.type,
    });

    cluster.members.forEach((m) => {
      let label = '';
      switch (cluster.type) {
        case 'flight':
          label = m.seat_number ? `siège ${m.seat_number}` : 'même vol';
          break;
        case 'phone':
          if (m.phone) label = `mobile · ${m.phone}`;
          else if (m.emergency_phone) label = `urgence · ${m.emergency_phone}`;
          else label = 'tel partagé';
          break;
        case 'residence':
          label = m.room_number ? `chambre ${m.room_number}` : 'même résidence';
          break;
        case 'origin':
          label = m.nationality ? `nat. ${m.nationality}` : 'même provenance';
          break;
      }
      links.push({
        source: hubId, target: m.public_id,
        label, clusterType: cluster.type,
      });
    });
  });

  return { nodes: Array.from(nodeMap.values()), links };
}

/* ============================================================
   Composant
   ============================================================ */
export function ForceGraph({
  clusters,
  height = 720,
  frozen = false,
}: {
  clusters: ClusterShape[];
  height?: number;
  /** Fige le layout (drag instantané, simulation inactive). */
  frozen?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const router = useRouter();
  const simRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);

  // ----- Rebuild complet sur changement de données -----
  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;
    const width = containerRef.current.clientWidth || 1000;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { nodes, links } = buildMergedGraph(clusters);
    if (nodes.length === 0) {
      svg.attr('viewBox', `0 0 ${width} ${height}`);
      svg.append('text')
        .attr('x', width / 2).attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#94A3B8').attr('font-size', 14)
        .text('Aucune relation à afficher pour ces filtres.');
      return;
    }

    // --- Densité : ajuste juste la taille des nœuds, labels toujours visibles ---
    const N = nodes.length;
    const HUB_RADIUS = N > 200 ? 22 : 28;
    const TRAV_RADIUS = N > 300 ? 9 : N > 150 ? 11 : 14;

    svg
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet');

    const g = svg.append('g');

    // Zoom + pan
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.15, 4])
      .on('zoom', (event) => g.attr('transform', event.transform.toString()));
    svg.call(zoom as any);

    // --- Pré-positionnement : hubs en cercle, voyageurs autour ----
    const hubs = nodes.filter((n) => n.kind === 'hub');
    const cx = width / 2;
    const cy = height / 2;
    const ringR = Math.min(width, height) * 0.32;
    hubs.forEach((h, i) => {
      const a = (i / Math.max(hubs.length, 1)) * Math.PI * 2 - Math.PI / 2;
      h.x = cx + Math.cos(a) * ringR;
      h.y = cy + Math.sin(a) * ringR;
    });
    // Voyageur → place près de son premier hub trouvé
    const firstHubFor = new Map<string, GraphNode>();
    links.forEach((l) => {
      const src: any = l.source;
      const tgt: any = l.target;
      if (typeof src === 'string' || typeof tgt === 'string') return;
      if (src.kind === 'hub' && tgt.kind === 'traveler' && !firstHubFor.has(tgt.id)) {
        firstHubFor.set(tgt.id, src);
      }
    });
    nodes.forEach((n) => {
      if (n.kind === 'traveler') {
        const h = firstHubFor.get(n.id);
        if (h && h.x != null && h.y != null) {
          n.x = h.x + (Math.random() - 0.5) * 80;
          n.y = h.y + (Math.random() - 0.5) * 80;
        } else {
          n.x = cx + (Math.random() - 0.5) * 200;
          n.y = cy + (Math.random() - 0.5) * 200;
        }
      }
    });

    // --- Simulation ----------------------------------------
    const linkDist = N > 200 ? 80 : 110;
    const chargeBase = N > 200 ? -150 : -260;
    const hubCharge = N > 200 ? -350 : -600;

    const sim = d3.forceSimulation<GraphNode>(nodes)
      .force('link', d3.forceLink<GraphNode, GraphLink>(links)
        .id((d) => d.id)
        .distance((l) => (l.clusterType === 'companion' ? linkDist * 0.7 : linkDist))
        .strength(0.55),
      )
      .force('charge', d3.forceManyBody().strength((d: any) => (d.kind === 'hub' ? hubCharge : chargeBase)))
      .force('center', d3.forceCenter(cx, cy))
      .force('collision', d3.forceCollide<GraphNode>().radius((d) => (d.kind === 'hub' ? HUB_RADIUS + 8 : TRAV_RADIUS + 4)))
      .force('x', d3.forceX(cx).strength(0.04))
      .force('y', d3.forceY(cy).strength(0.04))
      .alphaDecay(0.05)        // converge ~2× plus vite
      .velocityDecay(0.5);

    simRef.current = sim;

    // --- Links ---------------------------------------------
    const linkSel = g.append('g').attr('class', 'links')
      .selectAll('path')
      .data(links)
      .enter()
      .append('path')
      .attr('id', (_d, i) => `lp-${i}`)
      .attr('fill', 'none')
      .attr('stroke', (d) => TYPE_COLOR[d.clusterType])
      .attr('stroke-opacity', 0.5)
      .attr('stroke-width', (d) => (d.clusterType === 'companion' ? 2 : 1.4));

    // Labels d'arête (toujours visibles)
    g.append('g').attr('class', 'link-labels')
      .selectAll('text')
      .data(links)
      .enter()
      .append('text')
      .attr('font-size', 9)
      .attr('font-weight', 700)
      .attr('fill', '#475569')
      .attr('dy', -3)
      .append('textPath')
      .attr('href', (_d, i) => `#lp-${i}`)
      .attr('startOffset', '50%')
      .attr('text-anchor', 'middle')
      .text((d) => d.label);

    // --- Nodes ---------------------------------------------
    const nodeSel = g.append('g').attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .style('cursor', (d) => (d.kind === 'traveler' ? 'pointer' : 'default'))
      .on('click', (_e, d) => {
        if (d.kind === 'traveler' && d.member) {
          router.push(`/surveillance/${d.member.public_id}`);
        }
      })
      .call(
        d3.drag<SVGGElement, GraphNode>()
          .on('start', (event, d) => {
            if (!event.active && !frozen) sim.alphaTarget(0.2).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on('end', (event, d) => {
            if (!event.active) sim.alphaTarget(0);
            if (!frozen) { d.fx = null; d.fy = null; }
          }) as any,
      );

    // Hubs
    const hubGroup = nodeSel.filter((d) => d.kind === 'hub');
    hubGroup.append('circle')
      .attr('r', HUB_RADIUS)
      .attr('fill', (d) => TYPE_COLOR[d.clusterType!])
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 3)
      .attr('opacity', 0.95);
    hubGroup.append('text')
      .attr('text-anchor', 'middle').attr('dy', 4)
      .attr('font-size', 11).attr('font-weight', 900).attr('fill', '#ffffff')
      .text((d) => {
        const c = clusters.find((cc) => `__hub__${cc.key}` === d.id);
        return c ? String(c.size) : '';
      });
    hubGroup.append('text')
      .attr('text-anchor', 'middle').attr('dy', HUB_RADIUS + 14)
      .attr('font-size', 10).attr('font-weight', 800).attr('fill', '#0F172A')
      .text((d) => (d.label.length > 28 ? d.label.slice(0, 26) + '…' : d.label));

    // Travelers
    const travGroup = nodeSel.filter((d) => d.kind === 'traveler');
    travGroup.append('circle')
      .attr('r', TRAV_RADIUS)
      .attr('fill', (d) => STATUS_COLOR[d.status || ''] || '#94A3B8')
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 2);
    travGroup.append('text')
      .attr('text-anchor', 'middle').attr('dy', 3)
      .attr('font-size', 9).attr('font-weight', 900).attr('fill', '#ffffff')
      .text((d) => initials(d.label));
    travGroup.append('text')
      .attr('text-anchor', 'middle').attr('dy', TRAV_RADIUS + 14)
      .attr('font-size', 9).attr('font-weight', 700).attr('fill', '#334155')
      .text((d) => trim(d.label, 14));

    // <title> tooltip
    nodeSel.append('title').text((d) => {
      if (d.kind === 'hub') return d.label;
      const m = d.member!;
      return [
        m.full_name,
        m.public_id,
        m.flight ? `Vol ${m.flight}` + (m.seat_number ? ` · siège ${m.seat_number}` : '') : null,
        m.hotel ? `Hôtel ${m.hotel}` + (m.room_number ? ` · ch. ${m.room_number}` : '') : null,
        m.entry_point ? `Pt entrée ${m.entry_point}` : null,
      ].filter(Boolean).join('\n');
    });

    // ---- Tick : actualisation positions ----
    sim.on('tick', () => {
      linkSel.attr('d', (d) => {
        const s: any = d.source;
        const t: any = d.target;
        if (s.x == null || t.x == null) return '';
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dr = Math.sqrt(dx * dx + dy * dy) * 1.6;
        return `M${s.x},${s.y}A${dr},${dr} 0 0,1 ${t.x},${t.y}`;
      });
      nodeSel.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    // Si frozen au démarrage : fixer tout et arrêter la sim après quelques ticks
    if (frozen) {
      // Laisse 60 ticks pour pré-positionner puis fige
      for (let i = 0; i < 60; i++) sim.tick();
      nodes.forEach((n) => { n.fx = n.x; n.fy = n.y; });
      sim.stop();
      // Re-render des positions
      sim.tick();
    }

    return () => { sim.stop(); };
  }, [clusters, height, router, frozen]);

  return (
    <div
      ref={containerRef}
      className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-950 overflow-hidden"
    >
      <svg ref={svgRef} className="w-full block" style={{ height }} />
    </div>
  );
}

function initials(name: string) {
  return name
    .split(/\s+/).filter(Boolean).slice(0, 2)
    .map((p) => p[0]?.toUpperCase()).join('');
}
function trim(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}
