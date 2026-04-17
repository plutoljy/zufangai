# 前后端集成指南

## 已完成
✅ 创建 src/services/api.ts - API客户端模块

## 需要修改 src/App.tsx

### 1. 添加导入（第3行后）
import { uploadContract, analyzeContract, getReport } from './services/api';
import type { AnalysisEvent, AnalysisReport } from './services/api';

### 2. 在 App 组件中添加状态
const [contractId, setContractId] = useState<string | null>(null);
const [uploadedFile, setUploadedFile] = useState<File | null>(null);
const [analysisReport, setAnalysisReport] = useState<AnalysisReport | null>(null);

### 3. 修改 UploadView 组件
- 添加 useRef 用于文件输入
- 添加真实的文件上传逻辑
- 调用 uploadContract() API

### 4. 修改 AnalysisView 组件
- 使用 SSE 接收实时进度
- 调用 analyzeContract() API
- 根据事件类型更新进度

### 5. 修改组件传参
- UploadView 需要 setContractId 和 setUploadedFile
- AnalysisView 需要 contractId 和 setAnalysisReport

## 测试步骤

1. 启动后端：cd backend && python -m uvicorn src.main:app --reload
2. 启动前端：npm run dev
3. 测试上传和分析流程

详细代码修改请参考上面的说明。
