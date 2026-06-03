/**
 * 面试对话查看 - 增强版
 * 支持三种消息类型：宠物、候选人、房东插入
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, AlertTriangle, CheckCircle, Send } from 'lucide-react';

interface Message {
  id: string;
  sender: 'pet' | 'user' | 'landlord_interrupt';
  senderName?: string;  // 发送者名称（如：旺财、小明、房东）
  content: string;
  timestamp: string;
  flags?: string[];
  messageType?: 'question' | 'answer' | 'interrupt';  // 消息类型
}

interface MatchResult {
  score: number;
  dealBreakers: { item: string; triggered: boolean; reason: string }[];
  commonGrounds: string[];
  recommendation: string;
}

interface Props {
  candidateName: string;
  candidateId?: string;  // 新增：候选人ID，用于发送消息
  messages: Message[];
  matchResult?: MatchResult;
  onBack: () => void;
  onSendInterrupt?: (message: Message) => Promise<void>;  // 新增：发送插入消息的回调
}

export const InterviewView: React.FC<Props> = ({
  candidateName,
  candidateId,
  messages,
  matchResult,
  onBack,
  onSendInterrupt
}) => {
  const [userInput, setUserInput] = useState('');
  const [isSending, setIsSending] = useState(false);

  const handleSendInterrupt = async () => {
    if (!userInput.trim() || isSending) return;

    setIsSending(true);
    try {
      const newMessage: Message = {
        id: Date.now().toString(),
        sender: 'landlord_interrupt',
        senderName: '房东',
        content: userInput,
        timestamp: new Date().toLocaleTimeString('zh-CN', {
          hour: '2-digit',
          minute: '2-digit'
        }),
        messageType: 'interrupt'
      };

      // 调用父组件的回调函数
      if (onSendInterrupt) {
        await onSendInterrupt(newMessage);
      }

      setUserInput('');
    } catch (error) {
      console.error('发送失败:', error);
      alert('发送失败，请重试');
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendInterrupt();
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-4xl mx-auto"
      >
        {/* 头部 */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={onBack}
            className="p-3 bg-muted rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold">🐾 与 {candidateName} 的面试对话</h1>
            <p className="text-muted-foreground">宠物代理自动面试记录</p>
          </div>
        </div>

        {/* 对话记录 */}
        <div className="bg-card p-6 rounded-lg border-4 border-border shadow-brutal mb-6">
          <h2 className="font-bold mb-4">💬 对话记录</h2>
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {messages.map((msg, index) => {
              // 根据消息类型确定样式
              const isLandlordInterrupt = msg.sender === 'landlord_interrupt';
              const isPet = msg.sender === 'pet';
              const isUser = msg.sender === 'user';

              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, x: isPet ? -20 : isUser ? 20 : 0 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`flex ${
                    isLandlordInterrupt
                      ? 'justify-center'
                      : isUser
                        ? 'justify-end'
                        : 'justify-start'
                  }`}
                  data-sender={msg.sender}
                >
                  <div
                    className={`max-w-[70%] p-4 rounded-lg border-2 message-content ${
                      isLandlordInterrupt
                        ? 'bg-yellow-50 border-yellow-400 border-4'
                        : isPet
                          ? 'bg-blue-50 border-blue-200'
                          : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-sm font-bold ${
                        isLandlordInterrupt
                          ? 'text-yellow-900'
                          : isPet
                            ? 'text-blue-900'
                            : 'text-gray-900'
                      }`}>
                        {isLandlordInterrupt && '👨‍💼 房东'}
                        {isPet && `🐾 ${msg.senderName || '宠物'}`}
                        {isUser && `👤 ${msg.senderName || '候选人'}`}
                      </span>
                      <span className="text-xs text-muted-foreground">{msg.timestamp}</span>
                      {isLandlordInterrupt && (
                        <span className="text-xs bg-yellow-200 text-yellow-800 px-2 py-0.5 rounded">
                          💬 插入问题
                        </span>
                      )}
                    </div>
                    <p className={`text-sm ${
                      isLandlordInterrupt ? 'text-yellow-900 font-medium' : ''
                    }`}>
                      {msg.content}
                    </p>
                    {msg.flags && msg.flags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {msg.flags.map(flag => (
                          <span
                            key={flag}
                            className="px-2 py-0.5 text-xs bg-destructive/20 text-destructive rounded"
                          >
                            🚩 {flag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* 匹配结果 */}
        {matchResult && (
          <div className="bg-card p-6 rounded-lg border-4 border-border shadow-brutal">
            <h2 className="font-bold mb-4">📊 匹配分析</h2>

            {/* 总分 */}
            <div className="mb-6 p-4 bg-primary/10 rounded-lg border-2 border-primary">
              <div className="flex items-center justify-between">
                <span className="font-bold">总体匹配度</span>
                <span className="text-3xl font-bold text-primary">{matchResult.score}%</span>
              </div>
            </div>

            {/* 踩雷点分析 */}
            <div className="mb-6">
              <h3 className="font-bold mb-3 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                踩雷点检测
              </h3>
              <div className="space-y-2">
                {matchResult.dealBreakers.map((item, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg border-2 ${
                      item.triggered
                        ? 'bg-destructive/10 border-destructive'
                        : 'bg-muted border-border'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">{item.item}</span>
                      <span className={item.triggered ? 'text-destructive' : 'text-green-600'}>
                        {item.triggered ? '❌ 触发' : '✅ 未触发'}
                      </span>
                    </div>
                    {item.reason && (
                      <p className="text-sm text-muted-foreground">{item.reason}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* 共同点 */}
            {matchResult.commonGrounds.length > 0 && (
              <div className="mb-6">
                <h3 className="font-bold mb-3 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5" />
                  共同点
                </h3>
                <div className="flex flex-wrap gap-2">
                  {matchResult.commonGrounds.map((item, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-green-100 text-green-700 rounded-lg border-2 border-green-300"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 建议 */}
            <div className="p-4 bg-accent/10 rounded-lg border-2 border-accent">
              <h3 className="font-bold mb-2">💡 建议</h3>
              <p className="text-sm">{matchResult.recommendation}</p>
            </div>
          </div>
        )}
      </motion.div>

      {/* 房东插入消息输入框 - 固定在底部 */}
      <div className="fixed bottom-0 left-0 right-0 bg-card p-4 border-t-4 border-border shadow-lg z-10">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-2">
            <input
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="💬 房东插入问题或评论..."
              disabled={isSending}
              className="flex-1 px-4 py-3 border-2 border-border rounded-lg
                         focus:border-primary focus:outline-none
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-colors"
            />
            <button
              onClick={handleSendInterrupt}
              disabled={isSending || !userInput.trim()}
              className="px-6 py-3 bg-primary text-primary-foreground
                         rounded-lg border-2 border-border shadow-brutal
                         hover:translate-x-1 hover:translate-y-1 hover:shadow-none
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              {isSending ? '发送中...' : '发送'}
            </button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            💡 提示：你可以随时插入问题，候选人会收到通知
          </p>
        </div>
      </div>
    </div>
  );
};
