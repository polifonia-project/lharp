"""
A collection of utils to visualise chord progressions and harmonic similarities.
"""

import networkx as nx

import matplotlib.pyplot as plt

from bokeh.io import show, save
from bokeh.models import Circle, MultiLine, HoverTool, NodesAndLinkedEdges
from bokeh.plotting import figure, from_networkx
from bokeh.palettes import Greys256, Blues256, Spectral8
from bokeh.transform import linear_cmap


filtration_code = '''
    const new_sources = [];
    const new_targets = [];
    const new_weights = [];
    let n = sources.length;

    for (let i = 0; i < n; i++) {
        if (weights[i] >= this.value[0] && weights[i] <= this.value[1]) {
            new_sources.push(sources[i]);
            new_targets.push(targets[i]);
            new_weights.push(weights[i]);
        }
    }
    var new_data_edge = {'start': new_sources, 'end': new_targets, 'weight': new_weights};
    graph_setup.edge_renderer.data_source.data = new_data_edge;
    console.log('Min: ' + this.value[0] + ' Max: ' + this.value[1] + ' Filtered edges: ' + new_sources.length)
'''

node_info_code = '''
    var text = "";
    if (this.value in meta) {
        text='<b>Title:</b> ' + meta[this.value]['title'] + '<br>';
        text+='<b>Artist:</b> ' + meta[this.value]['artist'] + '<br>';
        text+='<b>Link:</b> ' + '<a href=' + meta[this.value]['link'] + ', target="_blank">Listen on Soundcloud</a>';
    } else {
        text=this.value + " was not found in the graph!";
    }
    div.text = text;
'''

def compute_similarity_graph(hsim_map:dict, encdec=None):
    """
    Computes an undirected graph from a nested dictionary expressing the
    harmonic similarity between each couple of tracks. Two nodes are connected
    if the similarity value among the corresponding tracks is greater than 0.
    Two additional labels describe the connection: the value of the similarity,
    and the longest recurrent pattern on which the similarity is based. If a
    decoder is provided as optional argument, the longest pattern is decoded.

    Args:
        hsim_map (dict): a symmetric dictionary where hsim_map["a"]["b"] gives
            the similarity among "a" and "b" if not null.
        encdec (EncoderDecoder): an optional encoder-decoder instance.

    Returns:
        G (nx.Graph): a graph representing the parwise similarities.
    """

    G = nx.Graph()

    for track_id in hsim_map.keys():
        if len(hsim_map[track_id]) > 0:
            G.add_node(track_id)

    for track_a in hsim_map:
        for track_b in hsim_map[track_a]:
            if not G.has_edge(track_b, track_a):
                hsim_val, lsrp = hsim_map[track_a][track_b]
                # Decode the longest shared recurrent pattern
                if encdec is not None:  # only if the decoder is given
                    lsrp = [encdec.decode_event(idx) for idx in lsrp]
                G.add_edge(track_a, track_b, weight=hsim_val, lsrp=lsrp)

    return G


def embed_network_analysis(G:nx.Graph, mod_palette=Spectral8):

    # Some basic network analysis
    degrees_dict = dict(nx.degree(G))
    communities = nx.algorithms.community.greedy_modularity_communities(G)

    mod_class, mod_color = {}, {}
    # Loop through each cluster in the network
    for community_number, community in enumerate(communities):
        # For cluster member, add their cluster number and a distinct color
        for name in community: 
            mod_class[name] = community_number
            mod_color[name] = mod_palette[community_number]
    # Add modularity class, colour, and degree as attributes
    nx.set_node_attributes(G, name='degree', values=degrees_dict)
    nx.set_node_attributes(G, mod_class, 'modularity_cls')
    nx.set_node_attributes(G, mod_color, 'modularity_col')
