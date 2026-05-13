-- =============================================================
-- Neo4j 图谱初始化 Cypher 脚本
-- 项目: 刑智·护苗
-- 执行方式: Neo4j Browser (http://localhost:7474) 或 cypher-shell
-- 执行时间: 首次部署时运行一次
-- =============================================================

// ---------------------------------------------------------------
// Step 1: 创建唯一约束（Unique Constraints）
// 保证节点不重复，且自动创建索引
// ---------------------------------------------------------------

// Person 节点：以身份证号为唯一键
CREATE CONSTRAINT person_sfzh IF NOT EXISTS
FOR (p:Person) REQUIRE p.sfzh IS UNIQUE;

// Case 节点：以案件编号为唯一键
CREATE CONSTRAINT case_ajbh IF NOT EXISTS
FOR (c:Case) REQUIRE c.ajbh IS UNIQUE;

// School 节点：以学校代码为唯一键（可选，后期扩展用）
CREATE CONSTRAINT school_code IF NOT EXISTS
FOR (s:School) REQUIRE s.code IS UNIQUE;


// ---------------------------------------------------------------
// Step 2: 创建普通索引（加速查询）
// ---------------------------------------------------------------

// Person 按姓名查询
CREATE INDEX person_name IF NOT EXISTS
FOR (p:Person) ON (p.name);

// Person 按未成年人标记过滤
CREATE INDEX person_is_wcnr IF NOT EXISTS
FOR (p:Person) ON (p.is_wcnr);

// Case 按案由（罪名）查询
CREATE INDEX case_aymc IF NOT EXISTS
FOR (c:Case) ON (c.aymc);

// Case 按发案时间查询
CREATE INDEX case_fasj IF NOT EXISTS
FOR (c:Case) ON (c.fasj);

// Case 按区域查询
CREATE INDEX case_area IF NOT EXISTS
FOR (c:Case) ON (c.area_code);


// ---------------------------------------------------------------
// Step 3: 示例节点结构（说明各节点属性）
// 实际数据由 ETL 脚本导入，这里仅作结构说明
// ---------------------------------------------------------------

// Person 节点属性说明：
// {
//   sfzh: "身份证号",       ← 唯一键
//   name: "姓名",
//   gender: "性别",
//   birth_date: "出生日期",
//   age: 17,
//   is_wcnr: true,          ← 是否未成年人
//   hjd: "户籍地",
//   jzdz: "居住地址",
//   area_code: "所属区域代码",
//   has_prior: true,        ← 是否有前科（冗余标记，加速过滤）
//   photo_id: "照片ID"      ← 关联人脸库
// }

// Case 节点属性说明：
// {
//   ajbh: "案件编号",       ← 唯一键
//   aymc: "案由名称",       ← 如"盗窃罪"
//   ajlx: "案件类型",
//   fasj: "发案时间",
//   area_code: "承办区域",
//   cbdw_mc: "承办单位",
//   is_theft: true          ← 是否盗窃类案件（冗余标记）
// }

// ---------------------------------------------------------------
// Step 4: 关系类型说明
// ---------------------------------------------------------------

// (Person)-[:SAME_CASE {case_no, case_date, aymc}]->(Case)
//   含义：嫌疑人涉及某案件
//   来源：ywdata.zq_zfba_xyrxx

// (Person)-[:CO_SUSPECT {case_no, case_date, aymc, weight}]->(Person)
//   含义：两人在同一案件中共同作案
//   来源：ywdata.zq_zfba_xyrxx 同案聚合
//   weight：共同涉案次数（多次共同作案权重累加）

// (Person)-[:HAS_PRIOR_RECORD {crime_type, record_date}]->(Person) [自环或标记]
//   含义：该人有盗窃前科记录
//   来源：ywdata.b_per_dqqkrygj
//   实现：实际用 Person.has_prior 属性标记，不需要自环关系

// ---------------------------------------------------------------
// Step 5: 验证脚本（安装完成后执行验证）
// ---------------------------------------------------------------

// 查看所有约束
// SHOW CONSTRAINTS;

// 查看所有索引
// SHOW INDEXES;

// 查询图谱概况
// MATCH (n) RETURN labels(n) AS type, count(n) AS count ORDER BY count DESC;

// 查询关系概况
// MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count ORDER BY count DESC;
