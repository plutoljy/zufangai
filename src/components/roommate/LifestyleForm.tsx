/**
 * 生活习惯问卷 - MVP 版本
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface LifestyleData {
  sleepTime: string;
  cleanliness: number;
  socialLevel: number;
  noiseLevel: number;
  smoking: boolean;
  pets: boolean;
  dealBreakers: string[];
}

interface Props {
  onSubmit: (data: LifestyleData) => void;
  onBack: () => void;
}

export const LifestyleForm: React.FC<Props> = ({ onSubmit, onBack }) => {
  const [data, setData] = useState<LifestyleData>({
    sleepTime: 'normal',
    cleanliness: 3,
    socialLevel: 3,
    noiseLevel: 3,
    smoking: false,
    pets: false,
    dealBreakers: [],
  });

  const [customDealBreaker, setCustomDealBreaker] = useState('');

  const dealBreakerOptions = [
    { id: 'smoking', label: '🚭 吸烟' },
    { id: 'pets', label: '🐕 养宠物' },
    { id: 'noise', label: '🔊 噪音' },
    { id: 'cleanliness', label: '🧹 不爱干净' },
    { id: 'guests', label: '👥 频繁带人回家' },
  ];

  const toggleDealBreaker = (id: string) => {
    setData(prev => ({
      ...prev,
      dealBreakers: prev.dealBreakers.includes(id)
        ? prev.dealBreakers.filter(x => x !== id)
        : [...prev.dealBreakers, id]
    }));
  };

  const addCustomDealBreaker = () => {
    if (customDealBreaker.trim() && !data.dealBreakers.includes(customDealBreaker.trim())) {
      setData(prev => ({
        ...prev,
        dealBreakers: [...prev.dealBreakers, customDealBreaker.trim()]
      }));
      setCustomDealBreaker('');
    }
  };

  const removeDealBreaker = (item: string) => {
    setData(prev => ({
      ...prev,
      dealBreakers: prev.dealBreakers.filter(x => x !== item)
    }));
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl mx-auto"
      >
        <h1 className="text-3xl font-bold mb-2">🐾 创建你的宠物画像</h1>
        <p className="text-muted-foreground mb-8">告诉我们你的生活习惯，我们会生成专属宠物代理</p>

        <div className="space-y-6 bg-card p-6 rounded-lg border-4 border-border shadow-brutal">
          {/* 作息时间 */}
          <div>
            <label className="block font-bold mb-2">⏰ 作息时间</label>
            <select
              value={data.sleepTime}
              onChange={e => setData({ ...data, sleepTime: e.target.value })}
              className="w-full p-3 border-2 border-border rounded-lg"
            >
              <option value="early">早睡早起 (22:00-6:00)</option>
              <option value="normal">正常作息 (23:00-7:00)</option>
              <option value="late">夜猫子 (1:00-9:00)</option>
            </select>
          </div>

          {/* 清洁程度 */}
          <div>
            <label className="block font-bold mb-2">🧹 清洁程度: {data.cleanliness}/5</label>
            <input
              type="range"
              min="1"
              max="5"
              value={data.cleanliness}
              onChange={e => setData({ ...data, cleanliness: parseInt(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>随意</span>
              <span>整洁</span>
            </div>
          </div>

          {/* 社交程度 */}
          <div>
            <label className="block font-bold mb-2">👥 社交程度: {data.socialLevel}/5</label>
            <input
              type="range"
              min="1"
              max="5"
              value={data.socialLevel}
              onChange={e => setData({ ...data, socialLevel: parseInt(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>宅</span>
              <span>社交达人</span>
            </div>
          </div>

          {/* 噪音容忍度 */}
          <div>
            <label className="block font-bold mb-2">🔊 噪音容忍度: {data.noiseLevel}/5</label>
            <input
              type="range"
              min="1"
              max="5"
              value={data.noiseLevel}
              onChange={e => setData({ ...data, noiseLevel: parseInt(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>安静</span>
              <span>热闹</span>
            </div>
          </div>

          {/* 吸烟和宠物 */}
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={data.smoking}
                onChange={e => setData({ ...data, smoking: e.target.checked })}
                className="w-5 h-5"
              />
              <span>🚬 我吸烟</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={data.pets}
                onChange={e => setData({ ...data, pets: e.target.checked })}
                className="w-5 h-5"
              />
              <span>🐕 我养宠物</span>
            </label>
          </div>

          {/* 踩雷点 */}
          <div>
            <label className="block font-bold mb-3">⚠️ 我的踩雷点（不可接受的行为）</label>

            {/* 快捷选项 */}
            <div className="flex flex-wrap gap-2 mb-3">
              {dealBreakerOptions.map(option => (
                <button
                  key={option.id}
                  onClick={() => toggleDealBreaker(option.id)}
                  className={`px-4 py-2 rounded-lg border-2 border-border transition-all ${
                    data.dealBreakers.includes(option.id)
                      ? 'bg-destructive text-destructive-foreground'
                      : 'bg-background hover:bg-muted'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>

            {/* 自定义输入 */}
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={customDealBreaker}
                onChange={(e) => setCustomDealBreaker(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addCustomDealBreaker()}
                placeholder="自定义踩雷点..."
                className="flex-1 p-2 border-2 border-border rounded-lg text-sm"
              />
              <button
                onClick={addCustomDealBreaker}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg border-2 border-border hover:bg-primary/90"
              >
                添加
              </button>
            </div>

            {/* 已选择的踩雷点 */}
            {data.dealBreakers.length > 0 && (
              <div className="p-3 bg-destructive/10 rounded-lg border-2 border-destructive/30">
                <div className="text-sm font-bold mb-2">已设置的踩雷点：</div>
                <div className="flex flex-wrap gap-2">
                  {data.dealBreakers.map(item => (
                    <span
                      key={item}
                      className="px-3 py-1 bg-destructive text-destructive-foreground rounded-lg text-sm flex items-center gap-2"
                    >
                      {item}
                      <button
                        onClick={() => removeDealBreaker(item)}
                        className="hover:opacity-70"
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
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
            className="flex-1 px-6 py-3 bg-primary text-primary-foreground rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
          >
            生成宠物画像 →
          </button>
        </div>
      </motion.div>
    </div>
  );
};
