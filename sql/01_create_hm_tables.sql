-- =============================================================
-- 刑智·护苗 (hm_) 系统自建表
-- Schema: jcgkzx_monitor
-- 前缀: hm_ (护苗系统，与原有 zq_/t_/b_ 前缀区分)
-- 创建时间: 2026-05-12
-- =============================================================

-- ---------------------------------------------------------------
-- 表1: hm_graph_sync_log
-- 用途: 记录 KingBase -> Neo4j ETL 同步任务日志
--       用于增量同步控制，避免重复导入
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_graph_sync_log (
    id              BIGSERIAL PRIMARY KEY,
    sync_type       VARCHAR(50)  NOT NULL,  -- 同步类型: case/suspect/wcnr_suspect/prior_record/checkin
    source_table    VARCHAR(100) NOT NULL,  -- 来源表名，如 ywdata.zq_zfba_xyrxx
    sync_start_time TIMESTAMP    NOT NULL,  -- 本次同步开始时间
    sync_end_time   TIMESTAMP,              -- 本次同步结束时间（NULL表示进行中）
    records_read    INTEGER DEFAULT 0,      -- 从源表读取的记录数
    nodes_created   INTEGER DEFAULT 0,      -- Neo4j中创建的节点数
    rels_created    INTEGER DEFAULT 0,      -- Neo4j中创建的关系数
    status          VARCHAR(20)  NOT NULL DEFAULT 'running',  -- running/success/failed
    error_msg       TEXT,                   -- 失败时的错误信息
    sync_cursor     TEXT,                   -- 增量游标（如最后处理的时间戳或ID）
    created_by      VARCHAR(50)  DEFAULT 'hm_etl_worker',
    CONSTRAINT chk_sync_status CHECK (status IN ('running', 'success', 'failed'))
);

COMMENT ON TABLE jcgkzx_monitor.hm_graph_sync_log IS '护苗系统 KingBase->Neo4j 同步日志';
COMMENT ON COLUMN jcgkzx_monitor.hm_graph_sync_log.sync_type IS '同步类型: case/suspect/wcnr_suspect/prior_record/checkin';
COMMENT ON COLUMN jcgkzx_monitor.hm_graph_sync_log.sync_cursor IS '增量同步游标，存储上次同步的最后时间戳或最大ID';

CREATE INDEX IF NOT EXISTS idx_hm_sync_log_type_time
    ON jcgkzx_monitor.hm_graph_sync_log (sync_type, sync_start_time DESC);

CREATE INDEX IF NOT EXISTS idx_hm_sync_log_status
    ON jcgkzx_monitor.hm_graph_sync_log (status);


-- ---------------------------------------------------------------
-- 表2: hm_gang_result
-- 用途: 缓存 Neo4j Louvain 社区发现的团伙结果
--       供前端快速查询，避免每次都运行图算法
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_gang_result (
    id              BIGSERIAL PRIMARY KEY,
    gang_id         VARCHAR(64)  NOT NULL,  -- 团伙ID: community_{louvain_component_id}
    run_id          VARCHAR(64)  NOT NULL,  -- 算法运行批次ID（UUID），同一次运行共享
    member_sfzh     VARCHAR(20)  NOT NULL,  -- 成员身份证号
    member_name     VARCHAR(50),            -- 成员姓名
    member_age      INTEGER,                -- 成员年龄
    is_wcnr         BOOLEAN DEFAULT FALSE,  -- 是否未成年人
    gang_size       INTEGER,                -- 该团伙总人数（冗余存储便于查询）
    centrality_score FLOAT,                 -- 介数中心度（越高越可能是组织者）
    algo_type       VARCHAR(30) DEFAULT 'louvain',  -- 算法类型
    computed_at     TIMESTAMP NOT NULL DEFAULT NOW(),  -- 计算时间
    case_types      TEXT,                   -- 涉案类型摘要（JSON数组字符串）
    area_code       VARCHAR(20),            -- 主要活动区域代码
    CONSTRAINT uq_hm_gang_member UNIQUE (run_id, member_sfzh)
);

COMMENT ON TABLE jcgkzx_monitor.hm_gang_result IS '护苗系统团伙挖掘结果缓存（Louvain社区发现）';
COMMENT ON COLUMN jcgkzx_monitor.hm_gang_result.run_id IS '每次运行Louvain算法生成新的run_id，前端展示最新run_id的结果';
COMMENT ON COLUMN jcgkzx_monitor.hm_gang_result.centrality_score IS '介数中心度，用于识别团伙组织者，分值越高越居于网络中心';

CREATE INDEX IF NOT EXISTS idx_hm_gang_result_run_gang
    ON jcgkzx_monitor.hm_gang_result (run_id, gang_id);

CREATE INDEX IF NOT EXISTS idx_hm_gang_result_sfzh
    ON jcgkzx_monitor.hm_gang_result (member_sfzh);

CREATE INDEX IF NOT EXISTS idx_hm_gang_result_computed
    ON jcgkzx_monitor.hm_gang_result (computed_at DESC);


-- ---------------------------------------------------------------
-- 查询：最新一次团伙挖掘结果（用于前端首次加载）
-- ---------------------------------------------------------------
-- SELECT gang_id, COUNT(*) AS size, MAX(centrality_score) AS max_centrality
-- FROM jcgkzx_monitor.hm_gang_result
-- WHERE run_id = (SELECT run_id FROM jcgkzx_monitor.hm_gang_result ORDER BY computed_at DESC LIMIT 1)
-- GROUP BY gang_id
-- ORDER BY size DESC;
