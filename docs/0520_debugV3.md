1. 现在"关系图谱"这个模块还是报错,你帮我分析下原因
 ERROR: Exception on /api/graph/person/445381xxxxxxxx0415 [GET]
Traceback (most recent call last):
  File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 1455, in wsgi_app
    response = self.full_dispatch_request()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 869, in full_dispatch_request
    rv = self.handle_user_exception(e)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 867, in full_dispatch_request
    rv = self.dispatch_request()
         ^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 852, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/modules/graph/routes.py", line 33, in person_graph
    result = build_person_graph(zjhm, depth, relations=relations, time_range=time_range)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/modules/graph/services/graph_builder.py", line 229, in build_person_graph
    _add_school(zjhm, nodes, edges)
  File "/app/modules/graph/services/graph_builder.py", line 346, in _add_school
    row = query_one(sql, {"zjhm": zjhm})
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/shared/db/kingbase.py", line 107, in query_one
    cursor.execute(sql, params)
  File "/usr/local/lib/python3.12/site-packages/psycopg2/extras.py", line 236, in execute
    return super().execute(query, vars)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
psycopg2.errors.UndefinedColumn: column "yxx" does not exist
LINE 2:         SELECT yxx FROM "ywdata"."b_per_qscxwcnr" WHERE zjhm...
                       ^

[2026-05-20 06:45:23,100] INFO: 172.30.0.1 - - [20/May/2026 06:45:23] "GET /api/graph/person/445381xxxxxxxx0415?depth=1&relations=suspected_in,co_suspect,guardian_of,studies_at,appeared_at,checked_in,lives_at,same_school,same_area HTTP/1.1" 500 -
2. "态势总览"的:案件类型分布,月度趋势,风险等级分布,辖区排名,实时预警,年龄分布,轨迹热力图还是什么数据都没有
3. 针对上面的问题,如果你有什么需要我到内网进行测试的工作的话,你就让codex编一个脚本,我拿到这个脚本到内网执行,将你需要确认的内容再发回给你
4. 现在我想修改下docker打包策略
  1. 我想将项目的models文件夹放在宿主机,就放在和app.env,docker-compose.yml文件的同一层目录,项目启动的时候就加载model文件夹内的模型,这样每次打包不用打那么多,你帮我分析下可行性,会不会影响速度,性能等