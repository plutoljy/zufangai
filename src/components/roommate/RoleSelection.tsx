/**
 * 身份选择页面 - 第一步
 */
import React from 'react';
import { motion } from 'framer-motion';
import { Home, Search } from 'lucide-react';

interface Props {
  onSelect: (role: 'landlord' | 'tenant') => void;
  onBack: () => void;
}

export const RoleSelection: React.FC<Props> = ({ onSelect, onBack }) => {
  return (
    <div className="min-h-screen bg-background p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-4xl mx-auto"
      >
        <h1 className="text-3xl font-bold mb-2 text-center">🐾 选择你的身份</h1>
        <p className="text-muted-foreground mb-12 text-center">
          让宠物代理帮你找到合适的合租伙伴
        </p>

        <div className="grid md:grid-cols-2 gap-6">
          {/* 有房找室友 */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onSelect('landlord')}
            className="bg-card p-8 rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all text-left"
          >
            <div className="w-20 h-20 bg-primary/20 rounded-full flex items-center justify-center text-4xl mb-4 border-4 border-border">
              <Home className="w-10 h-10" />
            </div>
            <h2 className="text-2xl font-bold mb-2">🏠 我有房源</h2>
            <p className="text-muted-foreground mb-4">
              我有房子，想找合适的室友一起合租
            </p>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <span className="text-primary">✓</span>
                <span>发布房源信息</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-primary">✓</span>
                <span>设置宠物代理筛选候选人</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-primary">✓</span>
                <span>查看匹配结果和面试记录</span>
              </li>
            </ul>
          </motion.button>

          {/* 找房找室友 */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onSelect('tenant')}
            className="bg-card p-8 rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all text-left"
          >
            <div className="w-20 h-20 bg-accent/20 rounded-full flex items-center justify-center text-4xl mb-4 border-4 border-border">
              <Search className="w-10 h-10" />
            </div>
            <h2 className="text-2xl font-bold mb-2">🔍 我找房源</h2>
            <p className="text-muted-foreground mb-4">
              我需要找房子，想找合适的室友一起合租
            </p>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <span className="text-accent">✓</span>
                <span>浏览可用房源</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-accent">✓</span>
                <span>让宠物代理参加面试</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-accent">✓</span>
                <span>查看匹配度和建议</span>
              </li>
            </ul>
          </motion.button>
        </div>

        <button
          onClick={onBack}
          className="mt-8 mx-auto block px-6 py-3 bg-muted rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
        >
          返回服务中心
        </button>
      </motion.div>
    </div>
  );
};
