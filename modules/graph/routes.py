from flask import request, jsonify
from . import graph_bp
from .services.graph_builder import build_person_graph, build_case_graph, expand_node, search_nodes
from .services.path_finder import find_shortest_path


@graph_bp.route("/person/<zjhm>", methods=["GET"])
def person_graph(zjhm):
    depth = request.args.get("depth", 1, type=int)
    depth = max(1, min(depth, 3))
    relations = request.args.get("relations", "").strip() or None
    time_range = request.args.get("time_range", "").strip() or None
    result = build_person_graph(zjhm, depth, relations=relations, time_range=time_range)
    if not result["nodes"]:
        return jsonify({"error": "not_found", "message": "未找到该人员"}), 404
    return jsonify(result)


@graph_bp.route("/case/<ajbh>", methods=["GET"])
def case_graph(ajbh):
    depth = request.args.get("depth", 1, type=int)
    depth = max(0, min(depth, 3))
    result = build_case_graph(ajbh, depth)
    if not result["nodes"]:
        return jsonify({"error": "not_found"}), 404
    return jsonify(result)


@graph_bp.route("/search", methods=["GET"])
def graph_search():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify({"error": "missing_keyword"}), 400
    node_type = request.args.get("type", "").strip() or None
    results = search_nodes(keyword, node_type)
    return jsonify({"results": results})


@graph_bp.route("/expand", methods=["POST"])
def graph_expand():
    data = request.get_json(silent=True) or {}
    node_id = (data.get("node_id") or "").strip()
    node_type = (data.get("node_type") or "").strip()
    direction = (data.get("direction") or "both").strip()

    if not node_id or not node_type:
        return jsonify({"error": "missing_params", "message": "需要node_id和node_type参数"}), 400

    return jsonify(expand_node(node_id, node_type, direction))


@graph_bp.route("/paths", methods=["GET"])
def shortest_path():
    from_zjhm = request.args.get("from", "").strip()
    to_zjhm = request.args.get("to", "").strip()
    max_hops = request.args.get("max_hops", 4, type=int)

    if not from_zjhm or not to_zjhm:
        return jsonify({"error": "missing_params", "message": "需要from和to参数"}), 400

    result = find_shortest_path(from_zjhm, to_zjhm, max_hops)
    return jsonify(result)
