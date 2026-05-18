PS C:\Users\So\Desktop\doc\code> python .\0518_test_ruizhi_api.py --api-key sk-1cac5cc6772740ceb7bf1abf75f849a9uxz5y6nlvyj9zcs9 --base-url https://10.2.164.106/v2 --insecure
C:\Users\So\Desktop\doc\code\0518_test_ruizhi_api.py:12: SyntaxWarning: invalid escape sequence '\s'
  python .\test_ruizhi_api.py --insecure --sample-file .\sample.txt --sample-image .\sample.png --sample-wav .\zh.wav
Base URL: https://10.2.164.106/v2
Output dir: ruizhi_api_test_out
Tests: models, model_retrieve, chat, chat_stream, tool_call, embeddings, rerank, tokens, translation, tts

[PASS] models                           status=200 elapsed=273ms models=16 text_model=ayenaspring-pro-001
[PASS] model_retrieve                   status=200 elapsed=288ms model=ayenaspring-pro-001
[PASS] chat                             status=200 elapsed=657ms model=ayenaspring-pro-001
[PASS] chat_stream                      status=200 elapsed=547ms model=ayenaspring-pro-001; read first stream chunks
[PASS] tool_call                        status=200 elapsed=589ms expects finish_reason=tool_calls if supported
[PASS] embeddings                       status=200 elapsed=378ms model=Qwen3-Embedding-0.6B
[PASS] rerank                           status=200 elapsed=293ms model=bge-reranker-base
[PASS] tokens                           status=200 elapsed=299ms model=ayenaspring-pro-001
[PASS] translation                      status=200 elapsed=843ms model=ayenaspring-pro-001
[PASS] tts                              status=200 elapsed=531ms model=ayenaaudio-001; saved=ruizhi_api_test_out\tts_test.wav

Summary: passed=10, failed=0, report=ruizhi_api_test_out\report.json