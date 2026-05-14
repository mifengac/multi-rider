-- =============================================================
-- 刑智·护苗 AI 侧自产数据表
-- Schema: jcgkzx_monitor
-- 前缀: hm_ai_
-- 创建时间: 2026-05-13
--
-- 设计原则:
-- 1. 生产库源表只读，不重复建设人口、案件、警情、旅店、车辆等大表。
-- 2. 图片/视频如果源库或接口能提供地址/引用，优先保存地址/引用。
-- 3. 只有没有地址、但系统必须留存原图时，才保存二进制图片 image_blob。
-- 4. YOLO 检测结果、人工复核、训练样本、模型版本属于系统自产数据，保存在项目表。
-- =============================================================

CREATE SCHEMA IF NOT EXISTS jcgkzx_monitor;


-- ---------------------------------------------------------------
-- 表1: hm_ai_behavior_label
-- 用途: 统一维护 YOLO 行为/物品/场所标签字典
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ai_behavior_label (
    id                   BIGSERIAL PRIMARY KEY,
    label_code           VARCHAR(64)  NOT NULL UNIQUE,  -- 标签编码，如 wheelie/gathering/controlled_tool
    label_name           VARCHAR(100) NOT NULL,         -- 标签名称，如 翘车头/聚集/携带管制器具
    label_category       VARCHAR(30)  NOT NULL,         -- behavior/object/place/person/vehicle/scene
    scenario_code        VARCHAR(50),                   -- theft/fight/sexual_assault/racing/general
    default_risk_weight  NUMERIC(8, 2) DEFAULT 0,       -- 默认风险权重，由评分模型引用
    enabled              BOOLEAN NOT NULL DEFAULT TRUE,
    description          TEXT,
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_hm_ai_behavior_label_category
        CHECK (label_category IN ('behavior', 'object', 'place', 'person', 'vehicle', 'scene', 'other'))
);

COMMENT ON TABLE jcgkzx_monitor.hm_ai_behavior_label IS '护苗系统 AI 行为/物品/场所标签字典';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_behavior_label.label_code IS '系统内部稳定编码，不直接依赖模型输出中文名';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_behavior_label.scenario_code IS '适用场景: theft/fight/sexual_assault/racing/general';


-- ---------------------------------------------------------------
-- 表2: hm_ai_model_version
-- 用途: 记录 YOLO/人脸/评分模型版本，保证检测结果可追溯
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ai_model_version (
    id                   BIGSERIAL PRIMARY KEY,
    model_version_id     VARCHAR(64)  NOT NULL UNIQUE,  -- 系统生成版本ID
    model_code           VARCHAR(64)  NOT NULL,         -- yolo26n_wcnr/yolo26s_wcnr/insightface/risk_score 等
    model_name           VARCHAR(100) NOT NULL,
    model_task           VARCHAR(40)  NOT NULL,         -- yolo_detection/face_recognition/risk_score
    version_name         VARCHAR(100) NOT NULL,         -- v20260513、训练批次名等
    model_file_uri       TEXT,                          -- 模型文件路径/对象存储地址/制品仓库地址
    config_uri           TEXT,                          -- 训练配置、推理配置地址
    label_config_json    TEXT,                          -- 标签配置(JSON字符串)
    train_dataset_version VARCHAR(100),                 -- 训练集版本
    metrics_json         TEXT,                          -- mAP/precision/recall/F1 等指标(JSON字符串)
    status               VARCHAR(20) NOT NULL DEFAULT 'staging', -- staging/active/archived/disabled
    published_by         VARCHAR(50),
    published_at         TIMESTAMP,
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_hm_ai_model_version_task
        CHECK (model_task IN ('yolo_detection', 'face_recognition', 'risk_score', 'other')),
    CONSTRAINT chk_hm_ai_model_version_status
        CHECK (status IN ('staging', 'active', 'archived', 'disabled'))
);

COMMENT ON TABLE jcgkzx_monitor.hm_ai_model_version IS '护苗系统 AI 模型版本表';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_model_version.metrics_json IS '训练/验证指标，JSON字符串保存，避免依赖特定JSON类型';

CREATE INDEX IF NOT EXISTS idx_hm_ai_model_version_code_status
    ON jcgkzx_monitor.hm_ai_model_version (model_code, status);


-- ---------------------------------------------------------------
-- 表3: hm_ai_media_asset
-- 用途: 原图/视频/抓拍帧资源索引
-- 说明: 有地址链接就保存 media_uri；没有地址但必须留存时，才保存 image_blob。
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ai_media_asset (
    id                   BIGSERIAL PRIMARY KEY,
    asset_id             VARCHAR(64)  NOT NULL UNIQUE,  -- 系统资源ID，可用hash/UUID
    source_system        VARCHAR(50)  NOT NULL,         -- video_cloud/local_upload/db_table/api
    source_table         VARCHAR(128),                  -- 来源表，如 ywdata.t_spy_ryrlgj_xx
    source_pk            VARCHAR(128),                  -- 来源主键或业务ID
    source_row_key       TEXT,                          -- 复合主键或游标(JSON字符串)
    parent_asset_id      VARCHAR(64),                   -- 父资源ID，如视频抽帧可追溯原视频资源
    media_type           VARCHAR(20)  NOT NULL,         -- image/video/frame/face/background
    uri_type             VARCHAR(20)  NOT NULL DEFAULT 'unknown', -- url/file_path/api_ref/db_column/blob/unknown
    media_uri            TEXT,                          -- 图片/视频地址、接口引用、文件路径；有地址时只存这里
    image_blob           BYTEA,                         -- 无地址且必须保存原图时使用
    mime_type            VARCHAR(80),                   -- image/jpeg/video/mp4 等
    file_size_bytes      BIGINT,
    content_hash         VARCHAR(128),                  -- 文件hash，便于去重
    face_id              VARCHAR(100),
    person_id            VARCHAR(100),
    sfzh                 VARCHAR(32),
    person_name          VARCHAR(80),
    age_estimate         INTEGER,
    device_id            VARCHAR(100),
    device_name          VARCHAR(200),
    shot_time            TIMESTAMP,
    longitude            NUMERIC(12, 8),
    latitude             NUMERIC(12, 8),
    place_name           VARCHAR(300),
    area_code            VARCHAR(20),
    download_status      VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/downloaded/skipped/failed
    detect_status        VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/processing/success/failed/skipped
    error_msg            TEXT,
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_hm_ai_media_asset_media_type
        CHECK (media_type IN ('image', 'video', 'frame', 'face', 'background', 'other')),
    CONSTRAINT chk_hm_ai_media_asset_uri_type
        CHECK (uri_type IN ('url', 'file_path', 'api_ref', 'db_column', 'blob', 'unknown')),
    CONSTRAINT chk_hm_ai_media_asset_download_status
        CHECK (download_status IN ('pending', 'downloaded', 'skipped', 'failed')),
    CONSTRAINT chk_hm_ai_media_asset_detect_status
        CHECK (detect_status IN ('pending', 'processing', 'success', 'failed', 'skipped'))
);

ALTER TABLE jcgkzx_monitor.hm_ai_media_asset
    ADD COLUMN IF NOT EXISTS parent_asset_id VARCHAR(64);

COMMENT ON TABLE jcgkzx_monitor.hm_ai_media_asset IS '护苗系统原图/视频/抓拍帧资源索引表';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_media_asset.media_uri IS '优先保存图片/视频地址、接口引用或文件路径';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_media_asset.image_blob IS '仅当没有地址且必须留存原图时保存二进制图片';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_media_asset.source_row_key IS '来源表复合键、接口游标或字段引用，JSON字符串';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_media_asset.parent_asset_id IS '父资源ID，视频抽帧等子资源可回溯到原始媒体';

CREATE INDEX IF NOT EXISTS idx_hm_ai_media_asset_source
    ON jcgkzx_monitor.hm_ai_media_asset (source_system, source_table, source_pk);

CREATE INDEX IF NOT EXISTS idx_hm_ai_media_asset_sfzh_time
    ON jcgkzx_monitor.hm_ai_media_asset (sfzh, shot_time DESC);

CREATE INDEX IF NOT EXISTS idx_hm_ai_media_asset_device_time
    ON jcgkzx_monitor.hm_ai_media_asset (device_id, shot_time DESC);

CREATE INDEX IF NOT EXISTS idx_hm_ai_media_asset_detect_status
    ON jcgkzx_monitor.hm_ai_media_asset (detect_status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_hm_ai_media_asset_hash
    ON jcgkzx_monitor.hm_ai_media_asset (content_hash);

CREATE INDEX IF NOT EXISTS idx_hm_ai_media_asset_parent
    ON jcgkzx_monitor.hm_ai_media_asset (parent_asset_id);


-- ---------------------------------------------------------------
-- 表4: hm_ai_yolo_run
-- 用途: YOLO 批量检测任务运行批次
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ai_yolo_run (
    id                   BIGSERIAL PRIMARY KEY,
    run_id               VARCHAR(64)  NOT NULL UNIQUE,  -- 批次ID
    task_name            VARCHAR(200),
    model_version_id     VARCHAR(64),                   -- 关联 hm_ai_model_version.model_version_id
    model_code           VARCHAR(64),
    source_scope         TEXT,                          -- 检测范围，如时间、区域、来源表条件(JSON字符串)
    scenario_code        VARCHAR(50),                   -- theft/fight/sexual_assault/racing/general
    status               VARCHAR(20) NOT NULL DEFAULT 'running', -- running/success/failed/canceled
    total_assets         INTEGER DEFAULT 0,
    processed_assets     INTEGER DEFAULT 0,
    detected_assets      INTEGER DEFAULT 0,
    detection_count      INTEGER DEFAULT 0,
    started_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at          TIMESTAMP,
    error_msg            TEXT,
    created_by           VARCHAR(50) DEFAULT 'hm_ai_worker',
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_hm_ai_yolo_run_status
        CHECK (status IN ('running', 'success', 'failed', 'canceled'))
);

COMMENT ON TABLE jcgkzx_monitor.hm_ai_yolo_run IS '护苗系统 YOLO 批量检测运行批次表';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_yolo_run.source_scope IS '任务范围配置，JSON字符串，如时间范围、区域、数据源、标签筛选';

CREATE INDEX IF NOT EXISTS idx_hm_ai_yolo_run_status_time
    ON jcgkzx_monitor.hm_ai_yolo_run (status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_hm_ai_yolo_run_model
    ON jcgkzx_monitor.hm_ai_yolo_run (model_version_id, started_at DESC);


-- ---------------------------------------------------------------
-- 表5: hm_ai_yolo_detection
-- 用途: YOLO 行为/物品/场所检测结果
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ai_yolo_detection (
    id                   BIGSERIAL PRIMARY KEY,
    detection_id         VARCHAR(64)  NOT NULL UNIQUE,  -- 系统检测结果ID
    run_id               VARCHAR(64),                   -- 关联 hm_ai_yolo_run.run_id
    asset_id             VARCHAR(64)  NOT NULL,         -- 关联 hm_ai_media_asset.asset_id
    model_version_id     VARCHAR(64),                   -- 关联 hm_ai_model_version.model_version_id
    scenario_code        VARCHAR(50),                   -- theft/fight/sexual_assault/racing/general
    label_code           VARCHAR(64)  NOT NULL,         -- 关联 hm_ai_behavior_label.label_code
    label_name           VARCHAR(100) NOT NULL,
    label_category       VARCHAR(30),                   -- behavior/object/place/person/vehicle/scene
    confidence           NUMERIC(7, 6),                 -- 0-1 置信度
    bbox_x               NUMERIC(10, 4),                -- 左上角x
    bbox_y               NUMERIC(10, 4),                -- 左上角y
    bbox_w               NUMERIC(10, 4),                -- 宽
    bbox_h               NUMERIC(10, 4),                -- 高
    bbox_json            TEXT,                          -- 多框、关键点、分割结果等扩展(JSON字符串)
    track_id             VARCHAR(100),                  -- 视频多帧跟踪ID
    sfzh                 VARCHAR(32),                   -- 若已做人脸/身份关联，记录身份证号
    person_name          VARCHAR(80),
    device_id            VARCHAR(100),
    shot_time            TIMESTAMP,
    longitude            NUMERIC(12, 8),
    latitude             NUMERIC(12, 8),
    place_name           VARCHAR(300),
    review_status        VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/confirmed/rejected/ignored
    review_result        VARCHAR(30),                   -- true_positive/false_positive/false_negative/other
    reviewer_id          VARCHAR(50),
    reviewer_name        VARCHAR(80),
    reviewed_at          TIMESTAMP,
    review_comment       TEXT,
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_hm_ai_yolo_detection_confidence
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    CONSTRAINT chk_hm_ai_yolo_detection_review_status
        CHECK (review_status IN ('pending', 'confirmed', 'rejected', 'ignored')),
    CONSTRAINT chk_hm_ai_yolo_detection_review_result
        CHECK (review_result IS NULL OR review_result IN ('true_positive', 'false_positive', 'false_negative', 'other'))
);

COMMENT ON TABLE jcgkzx_monitor.hm_ai_yolo_detection IS '护苗系统 YOLO 行为/物品/场所检测结果表';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_yolo_detection.bbox_json IS '扩展检测结果，JSON字符串，可保存多框、关键点、分割、多标签等';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_yolo_detection.review_result IS '人工复核后用于沉淀正负样本';

CREATE INDEX IF NOT EXISTS idx_hm_ai_yolo_detection_asset
    ON jcgkzx_monitor.hm_ai_yolo_detection (asset_id);

CREATE INDEX IF NOT EXISTS idx_hm_ai_yolo_detection_run
    ON jcgkzx_monitor.hm_ai_yolo_detection (run_id);

CREATE INDEX IF NOT EXISTS idx_hm_ai_yolo_detection_label_time
    ON jcgkzx_monitor.hm_ai_yolo_detection (label_code, shot_time DESC);

CREATE INDEX IF NOT EXISTS idx_hm_ai_yolo_detection_sfzh_time
    ON jcgkzx_monitor.hm_ai_yolo_detection (sfzh, shot_time DESC);

CREATE INDEX IF NOT EXISTS idx_hm_ai_yolo_detection_review
    ON jcgkzx_monitor.hm_ai_yolo_detection (review_status, created_at DESC);


-- ---------------------------------------------------------------
-- 表6: hm_ai_training_sample
-- 用途: 模型训练样本与人工标注闭环
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ai_training_sample (
    id                   BIGSERIAL PRIMARY KEY,
    sample_id            VARCHAR(64)  NOT NULL UNIQUE,  -- 样本ID
    asset_id             VARCHAR(64)  NOT NULL,         -- 关联 hm_ai_media_asset.asset_id
    detection_id         VARCHAR(64),                   -- 可来源于 YOLO 检测结果
    source_type          VARCHAR(40)  NOT NULL,         -- yolo_detection/manual_import/review_feedback/dispatch_feedback
    source_ref_id        VARCHAR(128),                  -- 来源业务ID
    sample_media_uri     TEXT,                          -- 训练样本导出路径；有地址时保存地址
    sample_image_blob    BYTEA,                         -- 无地址且训练必须留存图片时使用
    scenario_code        VARCHAR(50),
    label_code           VARCHAR(64),
    label_name           VARCHAR(100),
    sample_type          VARCHAR(30) NOT NULL DEFAULT 'unlabeled', -- positive/negative/hard_negative/unlabeled
    annotation_status    VARCHAR(20) NOT NULL DEFAULT 'unreviewed', -- unreviewed/labeled/approved/rejected
    annotation_json      TEXT,                          -- 标注框、分割、关键点等(JSON字符串)
    dataset_split        VARCHAR(20) DEFAULT 'pool',    -- train/val/test/pool
    dataset_version      VARCHAR(100),
    target_model_code    VARCHAR(64),                   -- 计划用于哪个模型训练
    quality_score        NUMERIC(7, 4),
    labeled_by           VARCHAR(50),
    labeled_at           TIMESTAMP,
    approved_by          VARCHAR(50),
    approved_at          TIMESTAMP,
    review_comment       TEXT,
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_hm_ai_training_sample_source
        CHECK (source_type IN ('yolo_detection', 'manual_import', 'review_feedback', 'dispatch_feedback', 'other')),
    CONSTRAINT chk_hm_ai_training_sample_type
        CHECK (sample_type IN ('positive', 'negative', 'hard_negative', 'unlabeled')),
    CONSTRAINT chk_hm_ai_training_sample_status
        CHECK (annotation_status IN ('unreviewed', 'labeled', 'approved', 'rejected')),
    CONSTRAINT chk_hm_ai_training_sample_split
        CHECK (dataset_split IN ('train', 'val', 'test', 'pool'))
);

COMMENT ON TABLE jcgkzx_monitor.hm_ai_training_sample IS '护苗系统 AI 模型训练样本与人工标注表';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_training_sample.sample_media_uri IS '训练样本图片地址/导出路径，优先保存地址';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_training_sample.sample_image_blob IS '仅当无地址且训练必须留存图片时保存二进制图片';
COMMENT ON COLUMN jcgkzx_monitor.hm_ai_training_sample.annotation_json IS '标注结果，JSON字符串，保存bbox、类别、标注工具版本等';

CREATE INDEX IF NOT EXISTS idx_hm_ai_training_sample_asset
    ON jcgkzx_monitor.hm_ai_training_sample (asset_id);

CREATE INDEX IF NOT EXISTS idx_hm_ai_training_sample_detection
    ON jcgkzx_monitor.hm_ai_training_sample (detection_id);

CREATE INDEX IF NOT EXISTS idx_hm_ai_training_sample_label_status
    ON jcgkzx_monitor.hm_ai_training_sample (label_code, annotation_status);

CREATE INDEX IF NOT EXISTS idx_hm_ai_training_sample_dataset
    ON jcgkzx_monitor.hm_ai_training_sample (target_model_code, dataset_version, dataset_split);


-- ---------------------------------------------------------------
-- 初始标签建议：对应申报书中 12 类行为/场景，可按实际模型标签继续补充
-- ---------------------------------------------------------------
INSERT INTO jcgkzx_monitor.hm_ai_behavior_label
    (label_code, label_name, label_category, scenario_code, default_risk_weight, description)
VALUES
    ('wheelie', '翘车头', 'behavior', 'racing', 20, '飙车炸街场景核心行为'),
    ('loud_racing', '炸街/追逐竞驶', 'behavior', 'racing', 20, '飙车炸街、追逐竞驶等行为'),
    ('wrong_way', '逆行', 'behavior', 'racing', 10, '车辆逆向行驶'),
    ('plate_occlusion', '遮挡号牌', 'vehicle', 'racing', 15, '遮挡、污损、遮蔽号牌'),
    ('gathering_3plus', '三人及以上聚集', 'behavior', 'general', 12, '三人及以上聚集'),
    ('long_stay', '长时间滞留', 'behavior', 'general', 10, '同一地点停留超过阈值'),
    ('frequent_gathering', '频繁聚集', 'behavior', 'general', 12, '短期多次聚集'),
    ('same_clothing_gathering', '统一着装聚集', 'behavior', 'general', 10, '疑似统一服装或团伙特征'),
    ('controlled_tool', '携带管制器具', 'object', 'fight', 25, '刀具、棍棒、钢管等'),
    ('burglary_tool', '携带撬盗工具', 'object', 'theft', 25, '撬棍、螺丝刀、液压剪等'),
    ('high_risk_place_entry', '出入高危场所', 'place', 'general', 15, '出入旅店、娱乐场所、废弃厂房等高危场所'),
    ('night_wandering', '深夜游荡', 'behavior', 'general', 12, '22:00至次日6:00异常游荡')
ON CONFLICT (label_code) DO UPDATE
SET label_name = EXCLUDED.label_name,
    label_category = EXCLUDED.label_category,
    scenario_code = EXCLUDED.scenario_code,
    default_risk_weight = EXCLUDED.default_risk_weight,
    description = EXCLUDED.description,
    updated_at = NOW();


-- ---------------------------------------------------------------
-- 典型查询：待检测资源
-- ---------------------------------------------------------------
-- SELECT asset_id, media_uri, source_table, source_pk, shot_time
-- FROM jcgkzx_monitor.hm_ai_media_asset
-- WHERE detect_status = 'pending'
-- ORDER BY shot_time DESC NULLS LAST
-- LIMIT 100;

-- ---------------------------------------------------------------
-- 典型查询：人工复核后沉淀训练样本
-- ---------------------------------------------------------------
-- INSERT INTO jcgkzx_monitor.hm_ai_training_sample (
--     sample_id, asset_id, detection_id, source_type, scenario_code,
--     label_code, label_name, sample_type, annotation_status, annotation_json
-- )
-- SELECT
--     detection_id || '_sample',
--     asset_id,
--     detection_id,
--     'review_feedback',
--     scenario_code,
--     label_code,
--     label_name,
--     CASE WHEN review_result = 'true_positive' THEN 'positive' ELSE 'negative' END,
--     'labeled',
--     bbox_json
-- FROM jcgkzx_monitor.hm_ai_yolo_detection
-- WHERE review_status IN ('confirmed', 'rejected')
--   AND review_result IN ('true_positive', 'false_positive');
