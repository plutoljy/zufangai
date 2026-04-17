# 代码审查发现的问题

## 手动检查发现的问题

### 1. main.py 问题

#### 问题1: SSE事件类型不匹配（中等严重）
**位置**: main.py 第120-132行

**问题**: SSE事件类型与前端 api.ts 定义不匹配
- 后端发送: `owl_complete`, `dog_complete`, `beaver_complete`, `cat_complete`
- 前端期望: `owl_analysis`, `dog_retrieval`, `beaver_calculation`, `cat_report`

**影响**: 前端无法正确接收和处理SSE事件，导致进度条不更新

**修复建议**:
```python
# 修改 main.py 第120-132行
yield f"data: {json.dumps({'type': 'owl_analysis', ...}, ensure_ascii=False)}\n\n"
yield f"data: {json.dumps({'type': 'dog_retrieval', ...}, ensure_ascii=False)}\n\n"
yield f"data: {json.dumps({'type': 'beaver_calculation', ...}, ensure_ascii=False)}\n\n"
yield f"data: {json.dumps({'type': 'cat_report', ...}, ensure_ascii=False)}\n\n"
```

#### 问题2: 缺少文件大小检查（高严重）
**位置**: main.py upload_contract函数

**问题**: 没有检查上传文件大小，可能导致内存溢出

**修复建议**:
```python
# 在第60行前添加
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
if len(content) > MAX_FILE_SIZE:
    raise HTTPException(status_code=413, detail="文件大小超过50MB限制")
```

#### 问题3: 文件类型验证不足（中等严重）
**位置**: main.py upload_contract函数

**问题**: 只检查文件扩展名，没有验证实际文件类型

**修复建议**: 添加 python-magic 或检查文件头

#### 问题4: 错误处理过于宽泛（低严重）
**位置**: main.py 第66-67行

**问题**: 
```python
except:
    text = content.decode('gbk')
```
裸except会捕获所有异常，包括KeyboardInterrupt

**修复建议**:
```python
except UnicodeDecodeError:
    text = content.decode('gbk', errors='ignore')
```

### 2. rental_analysis_graph.py 问题

#### 问题5: 全局Agent实例（低严重）
**位置**: 第41-44行

**问题**: Agent在模块级别初始化，可能导致状态共享问题

**修复建议**: 在 create_analysis_graph() 函数内初始化

### 3. 前端 api.ts 问题

#### 问题6: EventSource没有超时处理（中等严重）
**位置**: api.ts analyzeContract函数

**问题**: SSE连接可能永久挂起，没有超时机制

**修复建议**:
```typescript
export function analyzeContract(
  contractId: string,
  onEvent: (event: AnalysisEvent) => void,
  onError: (error: Error) => void,
  timeout: number = 60000  // 60秒超时
): EventSource {
  const eventSource = new EventSource(...);
  
  const timeoutId = setTimeout(() => {
    eventSource.close();
    onError(new Error('分析超时，请重试'));
  }, timeout);
  
  eventSource.onmessage = (event) => {
    clearTimeout(timeoutId);
    // ...
  };
  
  return eventSource;
}
```

#### 问题7: 缺少重连机制（低严重）
**位置**: api.ts analyzeContract函数

**问题**: SSE断开后不会自动重连

**修复建议**: 添加重连逻辑或使用 EventSource polyfill

## 等待 Codex CLI 检查结果...
