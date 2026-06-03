/**
 * 宠物形象选择页面
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface Props {
  onSubmit: (pet: { avatar: string; name: string; personality: string }) => void;
  onBack: () => void;
}

const petOptions = [
  { emoji: '🐶', name: '小狗', traits: ['热情', '忠诚', '活泼'] },
  { emoji: '🐱', name: '小猫', traits: ['独立', '优雅', '细腻'] },
  { emoji: '🐰', name: '兔子', traits: ['温柔', '安静', '可爱'] },
  { emoji: '🐼', name: '熊猫', traits: ['憨厚', '友善', '随和'] },
  { emoji: '🦊', name: '狐狸', traits: ['机智', '灵活', '聪明'] },
  { emoji: '🐻', name: '小熊', traits: ['温暖', '可靠', '稳重'] },
];

export const PetSelection: React.FC<Props> = ({ onSubmit, onBack }) => {
  const [selected, setSelected] = useState(petOptions[0]);
  const [customName, setCustomName] = useState('');
  const [personality, setPersonality] = useState('friendly');

  const handleSubmit = () => {
    onSubmit({
      avatar: selected.emoji,
      name: customName || selected.name,
      personality,
    });
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-3xl mx-auto"
      >
        <h1 className="text-3xl font-bold mb-2">🎨 创建你的宠物代理</h1>
        <p className="text-muted-foreground mb-8">
          选择一个宠物形象，它将代表你进行初步沟通
        </p>

        <div className="space-y-6 bg-card p-6 rounded-lg border-4 border-border shadow-brutal">
          {/* 宠物形象选择 */}
          <div>
            <label className="block font-bold mb-3">选择宠物形象</label>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
              {petOptions.map((pet) => (
                <button
                  key={pet.emoji}
                  onClick={() => setSelected(pet)}
                  className={`p-4 rounded-lg border-4 transition-all ${
                    selected.emoji === pet.emoji
                      ? 'border-primary bg-primary/10 scale-110'
                      : 'border-border bg-background hover:bg-muted'
                  }`}
                >
                  <div className="text-4xl mb-1">{pet.emoji}</div>
                  <div className="text-xs font-medium">{pet.name}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 预览 */}
          <div className="p-4 bg-muted rounded-lg border-2 border-border">
            <div className="flex items-center gap-4">
              <div className="text-6xl">{selected.emoji}</div>
              <div>
                <div className="font-bold text-lg mb-1">
                  {customName || selected.name}
                </div>
                <div className="flex flex-wrap gap-1">
                  {selected.traits.map((trait) => (
                    <span
                      key={trait}
                      className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded"
                    >
                      {trait}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 自定义名字 */}
          <div>
            <label className="block font-bold mb-2">给宠物起个名字（可选）</label>
            <input
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder={`默认：${selected.name}`}
              className="w-full p-3 border-2 border-border rounded-lg"
              maxLength={10}
            />
          </div>

          {/* 性格设置 */}
          <div>
            <label className="block font-bold mb-3">宠物性格</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setPersonality('friendly')}
                className={`p-3 rounded-lg border-2 transition-all ${
                  personality === 'friendly'
                    ? 'border-primary bg-primary/10'
                    : 'border-border bg-background hover:bg-muted'
                }`}
              >
                <div className="font-bold mb-1">😊 友好型</div>
                <div className="text-xs text-muted-foreground">
                  热情开朗，善于沟通
                </div>
              </button>
              <button
                onClick={() => setPersonality('professional')}
                className={`p-3 rounded-lg border-2 transition-all ${
                  personality === 'professional'
                    ? 'border-primary bg-primary/10'
                    : 'border-border bg-background hover:bg-muted'
                }`}
              >
                <div className="font-bold mb-1">🤓 专业型</div>
                <div className="text-xs text-muted-foreground">
                  严谨细致，注重细节
                </div>
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
            onClick={handleSubmit}
            className="flex-1 px-6 py-3 bg-primary text-primary-foreground rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
          >
            下一步 →
          </button>
        </div>
      </motion.div>
    </div>
  );
};
