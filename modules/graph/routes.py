from flask import request, jsonify
from . import graph_bp
from .services.graph_builder import build_person_graph, search_nodes
from .services.path_finder import find_shortest_path


@graph_bp.route("/person/<zjhm>", methods=["GET"])
def person_graph(zjhm):
    depth = request.args.get("depth", 1, type=int)
    depth = min(depth, 3)
    result = build_person_graph(zjhm, depth)
    if not result["nodes"]:
        return jsonify({"error": "not_found", "message": "未找到该人员"}), 404
    return jsonify(result)


@graph_bp.route("/search", methods=["GET"])
def graph_search():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify({"error": "missing_keyword"}), 400
    results = search_nodes(keyword)
    return jsonify({"results": results})


@graph_bp.route("/paths", methods=["GET"])
def shortest_path():
    from_zjhm = request.args.get("from", "").strip()
    to_zjhm = request.args.get("to", "").strip()
    max_hops = request.args.get("max_hops", 4, type=int)

    if not from_zjhm or not to_zjhm:
        return jsonify({"error": "missing_params", "message": "需要from和to参数"}), 400

    result = find_shortest_path(from_zjhm, to_zjhm, max_hops)
    return jsonify(result)
