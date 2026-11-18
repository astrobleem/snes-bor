"""Packing-independent lower bound for immutable 2x4 tile footprints.

One physical cell may satisfy several source-tile occurrences only if their
entire footprints agree where they overlap. Enumerate every maximal legal
coincidence clique, then solve the fractional cell-cover relaxation.
"""
import itertools
import networkx as nx
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix


def lower_bound(blocks):
    blocks=sorted(set(blocks))
    grids=[{(x,y):b[(y*2+x)*32:(y*2+x+1)*32] for y in range(4) for x in range(2)} for b in blocks]
    occurrences=[(i,x,y) for i in range(len(blocks)) for y in range(4) for x in range(2)]
    graph=nx.Graph();graph.add_nodes_from(range(len(occurrences)))
    for a,(i,x,y) in enumerate(occurrences):
        for b in range(a):
            j,xx,yy=occurrences[b]
            if i==j or grids[i][x,y]!=grids[j][xx,yy]:continue
            # Align the two designated cells at the same physical address.
            dx,dy=x-xx,y-yy
            shifted={(cx+dx,cy+dy):t for (cx,cy),t in grids[j].items()}
            if all(grids[i][p]==shifted[p] for p in grids[i].keys()&shifted.keys()):graph.add_edge(a,b)
    cliques=[sorted(c) for c in nx.find_cliques(graph)]
    rows=[];cols=[]
    for c,clique in enumerate(cliques):
        rows.extend(clique);cols.extend([c]*len(clique))
    matrix=csc_matrix((np.ones(len(rows)),(rows,cols)),shape=(len(occurrences),len(cliques)))
    result=linprog(np.ones(len(cliques)),A_ub=-matrix,b_ub=-np.ones(len(occurrences)),bounds=(0,None),method='highs')
    assert result.success,result.message
    return dict(occurrences=occurrences,cliques=cliques,
                dual_weights=(-result.ineqlin.marginals).tolist(),cell_bound=float(result.fun))
