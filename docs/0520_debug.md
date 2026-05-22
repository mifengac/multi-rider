1. 
INFO: WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
2. 
 ERROR: Exception on /api/graph/person/445302200905041512 [GET]
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