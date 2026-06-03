/**
 * 合租需求发布 - MVP 版本
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface RequestData {
  title: string;
  location: string;
  rentMin: number;
  rentMax: number;
  mode: 'quick' | 'deep';
}

interface Props {
  onSubmit: (data: RequestData) => void;
  onBack: () => void;
}

export const RequestForm: React.FC<Props> = ({ onSubmit, onBack }) => {
  const [data, setData] = useState<RequestData>({
    title: '',
    location: '',
    rentMin: 1000,
    rentMax: 3000,
    mode: 'quick',
  });

  return (
    <div className="min-h-screen bg-background p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl mx-auto"
      >
        <h1 className="text-3xl font-bold mb-2">🏠 发布合租需求</h1>
        <p className="text-muted-foreground mb-8">填写房源信息，开始寻找合适的室友</p>

        <div className="space-y-6 bg-card p-6 rounded-lg border-4 border-border shadow-brutal">
          {/* 标题 */}
          <div>
            <label className="block font-bold mb-2">📝 需求标题</label>
            <input
              type="text"
              value={data.title}
              onChange={e => setData({ ...data, title: e.target.value })}
              placeholder="例如：寻找爱干净的室友合租两居室"
              className="w-full p-3 border-2 border-border rounded-lg"
            />
          </div>

          {/* 位置 */}
          <div>
            <label className="block font-bold mb-2">📍 位置</label>
            <input
              type="text"
              value={data.location}
              onChange={e => setData({ ...data, location: e.target.value })}
              placeholder="例如：北京朝阳区"
              className="w-full p-3 border-2 border-border rounded-lg"
            />
          </div>

          {/* 租金范围 */}
          <div>
            <label className="block font-bold mb-2">💰 租金范围（元/月）</label>
            <div className="flex gap-4 items-center">
              <input
                type="number"
                value={data.rentMin}
                onChange={e => setData({ ...data, rentMin: parseInt(e.target.value) })}
                className="flex-1 p-3 border-2 border-border rounded-lg"
              />
              <span>-</span>
              <input
                type="number"
                value={data.rentMax}
                onChange={e => setData({ ...data, rentMax: parseInt(e.target.value) })}
                className="flex-1 p-3 border-2 border-border rounded-lg"
              />
            </div>
          </div>

          {/* 面试模式 */}
          <div>
            <label className="block font-bold mb-3">🎯 面试模式</label>
            <div className="grid grid-cols-1 gap-4">
              <button
                onClick={() => setData({ ...data, mode: 'quick' })}
                className={`p-4 rounded-lg border-4 border-border transition-all text-left ${
                  data.mode === 'quick'
                    ? 'bg-primary text-primary-foreground shadow-brutal'
                    : 'bg-background hover:bg-muted'
                }`}
              >
                <div className="font-bold mb-2">⚡ 快速模式（5个核心问题）</div>
                <ul className="text-sm space-y-1 opacity-90">
                  <li>• 作息时间和生活习惯</li>
                  <li>• 清洁和卫生标准</li>
                  <li>• 社交和访客频率</li>
                  <li>• 吸烟和宠物情况</li>
                  <li>• 租金分摊和费用</li>
                </ul>
              </button>
              <button
                onClick={() => setData({ ...data, mode: 'deep' })}
                className={`p-4 rounded-lg border-4 border-border transition-all text-left ${
                  data.mode === 'deep'
                    ? 'bg-primary text-primary-foreground shadow-brutal'
                    : 'bg-background hover:bg-muted'
                }`}
              >
                <div className="font-bold mb-2">🔍 深度模式（10个详细问题）</div>
                <ul className="text-sm space-y-1 opacity-90">
                  <li>• 快速模式的所有问题</li>
                  <li>• 工作和学习时间安排</li>
                  <li>• 饮食习惯和厨房使用</li>
                  <li>• 噪音容忍度和安静时间</li>
                  <li>• 个人空间和隐私需求</li>
                  <li>• 长期规划和租期预期</li>
                </ul>
              </button>
            </div>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-4 mt-6">
          <button
            onClick={onBack}
            className="flex-1 px-6 py-3 bg-muted rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
          >
            返回
          </button>
          <button
            onClick={() => onSubmit(data)}
            disabled={!data.title || !data.location}
            className="flex-1 px-6 py-3 bg-primary text-primary-foreground rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            发布需求 →
          </button>
        </div>
      </motion.div>
    </div>
  );
};
