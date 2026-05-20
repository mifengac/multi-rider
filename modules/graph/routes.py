from flask import request, jsonify
from . import graph_bp
from .services.graph_builder import build_person_graph, build_case_graph, expand_node, search_nodes
from .services.path_finder import find_shortest_path
from shared.validators import (
    parse_int_arg,
    validate_allowed,
    validate_depth,
    validate_int_range,
    validate_relations,
    validate_time_range,
    validate_zjhm,
)


@graph_bp.route("/person/<zjhm>", methods=["GET"])
def person_graph(zjhm):
    if not validate_zjhm(zjhm):
        return jsonify({"error": "invalid_zjhm", "message": "证件号格式不正确"}), 400

    depth = parse_int_arg(request.args.get("depth"), 1)
    if not validate_depth(depth):
        return jsonify({"error": "invalid_depth", "message": "depth 必须为 1-3"}), 400

    relations = request.args.get("relations", "").strip() or None
    if not validate_relations(relations):
        return jsonify({"error": "invalid_relations", "message": "relations 参数不支持"}), 400

    time_range = request.args.get("time_range", "").strip() or None
    if not validate_time_range(time_range):
        return jsonify({"error": "invalid_time_range", "message": "time_range 必须为 1m/3m/6m/1y"}), 400

    result = build_person_graph(zjhm, depth, relations=relations, time_range=time_range)
    if not result["nodes"]:
        return jsonify({"error": "not_found", "message": "未找到该人员"}), 404
    return jsonify(result)


@graph_bp.route("/case/<ajbh>", methods=["GET"])
def case_graph(ajbh):
    if not str(ajbh or "").strip():
        return jsonify({"error": "invalid_ajbh", "message": "案件编号不能为空"}), 400

    depth = parse_int_arg(request.args.get("depth"), 1)
    if not validate_depth(depth):
        return jsonify({"error": "invalid_depth", "message": "depth 必须为 1-3"}), 400

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
    if node_type and not validate_allowed(node_type, {"person", "case", "school", "guardian", "location", "organization"}):
        return jsonify({"error": "invalid_type"}), 400
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
    if not validate_allowed(node_type, {"person", "case", "school", "guardian", "location", "organization"}):
        return jsonify({"error": "invalid_node_type"}), 400
    if not validate_allowed(direction, {"in", "out", "both"}):
        return jsonify({"error": "invalid_direction"}), 400

    return jsonify(expand_node(node_id, node_type, direction))


@graph_bp.route("/paths", methods=["GET"])
def shortest_path():
    from_zjhm = request.args.get("from", "").strip()
    to_zjhm = request.args.get("to", "").strip()
    max_hops = parse_int_arg(request.args.get("max_hops"), 4)

    if not from_zjhm or not to_zjhm:
        return jsonify({"error": "missing_params", "message": "需要from和to参数"}), 400
    if not validate_zjhm(from_zjhm) or not validate_zjhm(to_zjhm):
        return jsonify({"error": "invalid_zjhm"}), 400
    if not validate_int_range(max_hops, 1, 6):
        return jsonify({"error": "invalid_max_hops"}), 400

    result = find_shortest_path(from_zjhm, to_zjhm, max_hops)
    return jsonify(result)
