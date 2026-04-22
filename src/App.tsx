import { useState, useEffect, useRef } from 'react';
import type { CSSProperties, ChangeEvent, DragEvent, KeyboardEvent, ReactNode } from 'react';
import { UploadCloud, FileText, FileImage, File, Lock, Mail, ArrowRight, Loader2, MessageCircle, History, Settings, LogOut, Send, Download, Plus, ZoomIn, ZoomOut, AlertTriangle, CheckCircle2, MapPin, Edit2, FileCheck, User } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import {
  analyzeContract,
  cleanupBurnAfterReading,
  getReport,
  uploadContract,
} from './services/api';
import type { AnalysisReport, AnalysisEvent } from './services/api';
import { detectUploadFormat, getUploadAccept, getUploadHint, openNativeFileDialog, validateUploadSelection } from './uploadHelpers';
import type { UploadFormat, UploadTargetFormat } from './uploadHelpers';
import WorkspaceResultView from './components/WorkspaceResultView';
import LiveAnalysisStage from './components/LiveAnalysisStage';
import { UserPreferencesSettings } from './components/UserPreferencesSettings';
import { shouldRenderGlobalModal } from './utils/globalModalVisibility';
import {
  getCurrentSession,
  getRentalProfile,
  loginWithPassword,
  logout as logoutFromSupabase,
  onAuthStateChange,
  registerWithPassword,
} from './services/authService';
import { hasSupabaseConfig } from './services/supabase';
import type { RentalProfile } from './services/authService';
import type { Session, User as SupabaseUser } from '@supabase/supabase-js';

const AnimalIcon = ({ type, theme, className = "" }: { type: string, theme: string, className?: string }) => {
  const isDark = theme === 'dark';
  
  // 使用内联样式 (Inline Styles) 进行绝对定位，确保在 DOM 渲染的第一帧就处于正确位置。
  // 这样可以彻底解决 Tailwind 类名解析延迟导致的“先并列显示，再跳一帧结合”的闪烁问题。
  const containerStyle: CSSProperties = {
    position: 'relative',
    display: 'inline-block',
    width: '1em',
    height: '1em',
    lineHeight: 1,
  };

  const centerStyle: CSSProperties = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    fontSize: '1em',
    zIndex: 10,
  };

  if (type === 'owl') {
    return (
      <div className={className} style={containerStyle}>
        <span style={centerStyle}>🦉</span>
        {isDark && (
          <>
            <span style={{ position: 'absolute', bottom: '-10%', right: '-15%', fontSize: '0.55em', transform: 'rotate(-12deg)', zIndex: 20, filter: 'drop-shadow(0 4px 3px rgba(0,0,0,0.3))' }}>☕</span>
            <span className="animate-pulse" style={{ position: 'absolute', top: '-10%', right: '-5%', fontSize: '0.4em', zIndex: 20 }}>♨️</span>
          </>
        )}
      </div>
    );
  }
  if (type === 'dog') {
    return (
      <div className={className} style={containerStyle}>
        {isDark && (
          <div className="animate-pulse" style={{ position: 'absolute', top: '30%', left: '-40%', width: '80%', height: '80%', backgroundColor: 'rgba(253, 224, 71, 0.4)', borderRadius: '50%', filter: 'blur(12px)', zIndex: 0 }}></div>
        )}
        <span style={centerStyle}>🐶</span>
        {isDark && (
          <span style={{ position: 'absolute', bottom: '0%', left: '-15%', fontSize: '0.55em', transform: 'rotate(-60deg)', zIndex: 20, filter: 'drop-shadow(0 4px 3px rgba(0,0,0,0.3))' }}>🔦</span>
        )}
      </div>
    );
  }
  if (type === 'beaver') {
    return (
      <div className={className} style={containerStyle}>
        <span style={centerStyle}>🦫</span>
        {isDark && (
          <>
            <span style={{ position: 'absolute', bottom: '-15%', right: '0%', fontSize: '0.6em', transform: 'rotate(12deg)', zIndex: 20, filter: 'drop-shadow(0 4px 3px rgba(0,0,0,0.3))' }}>🧮</span>
            <span className="animate-bounce font-mono font-black text-secondary" style={{ position: 'absolute', top: '-10%', left: '-10%', fontSize: '0.35em', zIndex: 20 }}>∑</span>
            <span className="animate-ping font-mono font-black text-accent" style={{ position: 'absolute', top: '10%', right: '-10%', fontSize: '0.3em', zIndex: 20 }}>%</span>
          </>
        )}
      </div>
    );
  }
  if (type === 'cat') {
    return (
      <div className={className} style={containerStyle}>
        <span style={centerStyle}>🐱</span>
        {isDark && (
          <>
            <span style={{ position: 'absolute', bottom: '-15%', right: '-5%', fontSize: '0.6em', transform: 'rotate(-12deg)', zIndex: 20, filter: 'drop-shadow(0 4px 3px rgba(0,0,0,0.3))' }}>✍️</span>
            <span style={{ position: 'absolute', bottom: '-5%', left: '-15%', fontSize: '0.5em', transform: 'rotate(12deg)', zIndex: 10, filter: 'drop-shadow(0 4px 3px rgba(0,0,0,0.3))' }}>📄</span>
          </>
        )}
      </div>
    );
  }
  return <div className={className} style={containerStyle}><span style={centerStyle}>❓</span></div>;
};

// --- Login & Upload Views (Kept mostly the same, just adjusted wrapper for full screen) ---
const LoginView = ({
  onAuthenticate,
  theme,
}: {
  onAuthenticate: (payload: {
    mode: 'login' | 'register';
    email: string;
    password: string;
    username?: string;
  }) => Promise<void>;
  theme: string;
}) => {
  const [isLogin, setIsLogin] = useState(true);
  const [slideIndex, setSlideIndex] = useState(0);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [authError, setAuthError] = useState('');

  const slides = [
    { type: 'owl', title: '猫头鹰解析师', desc: '逐字阅读合同，精准揪出隐藏的霸王条款。' },
    { type: 'dog', title: '猎犬检索师', desc: '狂翻《民法典》，为你匹配最强维权案例。' },
    { type: 'beaver', title: '海狸计算师', desc: '精打细算，拒绝乱收水电费和不合理押金。' },
    { type: 'cat', title: '橘猫报告师', desc: '排版避坑指南，一键生成维权投诉书。' },
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setSlideIndex((prev) => (prev + 1) % slides.length);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  const handleSubmit = async () => {
    setAuthError('');

    if (!email.trim() || !password.trim()) {
      setAuthError('请先填写邮箱和密码。');
      return;
    }

    if (!isLogin && username.trim().length < 3) {
      setAuthError('用户名至少需要 3 个字符。');
      return;
    }

    if (!hasSupabaseConfig()) {
      setAuthError('还没有配置 Supabase，请先补充前端环境变量。');
      return;
    }

    try {
      setSubmitting(true);
      await onAuthenticate({
        mode: isLogin ? 'login' : 'register',
        email: email.trim(),
        password,
        username: isLogin ? undefined : username.trim(),
      });
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : '认证失败，请稍后重试。');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex-1 w-full p-4 sm:p-8 flex flex-col">
      <div className="m-auto w-full max-w-4xl flex flex-col md:flex-row bg-surface border-4 border-ink rounded-3xl shadow-[8px_8px_0px_var(--color-ink)] overflow-hidden shrink-0">
        
        {/* Left: Sliding Carousel (Hidden on small screens) */}
        <div className="hidden md:flex flex-col justify-center w-1/2 bg-secondary p-8 border-r-4 border-ink relative overflow-hidden">
          <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(#2D3142 2px, transparent 2px)', backgroundSize: '20px 20px' }}></div>
          <div className="relative z-10 h-64 flex flex-col items-center justify-center text-center">
            <AnimatePresence mode="wait">
              <motion.div
                key={slideIndex}
                initial={{ opacity: 0, x: -50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 50 }}
                transition={{ duration: 0.3 }}
                className="flex flex-col items-center"
              >
                <div className="text-7xl mb-4"><AnimalIcon type={slides[slideIndex].type} theme={theme} /></div>
                <h2 className="text-2xl font-black text-ink mb-2">{slides[slideIndex].title}</h2>
                <p className="text-ink/80 font-bold">{slides[slideIndex].desc}</p>
              </motion.div>
            </AnimatePresence>
          </div>
          {/* Slide Indicators */}
          <div className="flex justify-center gap-2 mt-8 relative z-10">
            {slides.map((_, i) => (
              <button 
                key={i} 
                onClick={() => setSlideIndex(i)}
                className={`h-2 rounded-full transition-all duration-300 cursor-pointer ${i === slideIndex ? 'w-8 bg-ink' : 'w-2 bg-ink/30 hover:bg-ink/50'}`} 
                aria-label={`Go to slide ${i + 1}`}
              />
            ))}
          </div>
        </div>

        {/* Right: Login/Register Form */}
        <div className="w-full md:w-1/2 p-8 relative bg-surface">
          <div className="absolute -top-4 -right-4 text-6xl opacity-10 transform rotate-12">🐾</div>
          
          <div className="mb-8 text-center relative z-10 md:hidden">
            <h1 className="text-3xl font-black mb-2 text-ink flex items-center justify-center gap-2">
              🐶 租房护卫队
            </h1>
            <p className="text-sm font-bold text-gray-custom">大学生防坑专属神器</p>
          </div>

          {/* Sliding Toggle */}
          <div className="flex relative bg-paper border-4 border-ink rounded-2xl p-1 mb-8 z-10">
            <div 
              className="absolute top-1 bottom-1 w-[calc(50%-4px)] bg-primary border-2 border-ink rounded-xl transition-transform duration-300 ease-in-out shadow-[2px_2px_0px_var(--color-ink)]"
              style={{ transform: isLogin ? 'translateX(0)' : 'translateX(100%)' }}
            />
            <button 
              onClick={() => setIsLogin(true)} 
              className={`flex-1 py-2 text-sm font-black relative z-10 transition-colors ${isLogin ? 'text-ink' : 'text-gray-custom hover:text-ink'}`}
            >
              登录
            </button>
            <button 
              onClick={() => setIsLogin(false)} 
              className={`flex-1 py-2 text-sm font-black relative z-10 transition-colors ${!isLogin ? 'text-ink' : 'text-gray-custom hover:text-ink'}`}
            >
              注册
            </button>
          </div>

          <div className="space-y-5 mb-8 relative z-10 min-h-[180px]">
            <AnimatePresence mode="wait">
              <motion.div
                key={isLogin ? 'login' : 'register'}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="space-y-5"
              >
                {!isLogin && (
                  <div>
                    <label className="block text-sm font-black text-ink mb-2">昵称</label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-custom text-lg">👤</span>
                      <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="你的称呼"
                        className="w-full border-4 border-ink rounded-xl p-3 pl-10 text-sm font-bold focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all bg-paper"
                      />
                    </div>
                  </div>
                )}
                <div>
                  <label className="block text-sm font-black text-ink mb-2">邮箱地址</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-custom" size={20} />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="student@edu.cn"
                      className="w-full border-4 border-ink rounded-xl p-3 pl-10 text-sm font-bold focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all bg-paper"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-black text-ink mb-2">密码</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-custom" size={20} />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full border-4 border-ink rounded-xl p-3 pl-10 text-sm font-bold focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all bg-paper"
                    />
                  </div>
                </div>
                {authError && (
                  <div className="rounded-xl border-4 border-ink bg-accent/10 text-accent p-3 text-sm font-black">
                    {authError}
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="w-full bg-accent text-white border-4 border-ink rounded-xl p-4 text-base font-black flex items-center justify-center gap-2 shadow-[4px_4px_0px_var(--color-ink)] hover:-translate-y-1 hover:shadow-[6px_6px_0px_var(--color-ink)] active:translate-y-1 active:shadow-none transition-all relative z-10 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {submitting ? '处理中...' : isLogin ? '进入工作台' : '创建测试账号'} <ArrowRight size={20} strokeWidth={3} />
          </button>
        </div>
      </div>
    </div>
  );
};

const FormatCard = ({ type, icon, label, selected, onClick }: { type: string, icon: ReactNode, label: string, selected: boolean, onClick: () => void }) => (
  <div
    onClick={onClick}
    className={`p-6 border-4 rounded-2xl cursor-pointer flex flex-col items-center justify-center gap-4 transition-all ${selected ? 'border-ink bg-secondary shadow-[4px_4px_0px_var(--color-ink)] scale-105' : 'border-ink/20 bg-surface hover:border-ink/50'}`}
  >
    <div className={selected ? 'text-ink' : 'text-gray-custom'}>{icon}</div>
    <span className="text-sm font-black text-center text-ink">{label}</span>
  </div>
);

const UploadView = ({ onUpload, location, setLocation }: { onUpload: () => void, location: string | null, setLocation: (loc: string) => void }) => {
  const [selectedFormat, setSelectedFormat] = useState('pdf');
  const [isLocating, setIsLocating] = useState(false);
  const [showLocationPicker, setShowLocationPicker] = useState(false);

  const cities = [
    { province: '北京市', cities: ['东城区', '西城区', '朝阳区', '海淀区', '丰台区', '石景山区', '通州区', '昌平区', '大兴区', '顺义区'] },
    { province: '上海市', cities: ['黄浦区', '徐汇区', '长宁区', '静安区', '普陀区', '虹口区', '杨浦区', '浦东新区', '闵行区', '宝山区'] },
    { province: '广东省', cities: ['广州市', '深圳市', '珠海市', '佛山市', '东莞市', '中山市', '惠州市'] },
    { province: '浙江省', cities: ['杭州市', '宁波市', '温州市', '嘉兴市', '湖州市', '绍兴市'] },
    { province: '江苏省', cities: ['南京市', '苏州市', '无锡市', '常州市', '南通市', '扬州市'] },
    { province: '四川省', cities: ['成都市', '绵阳市', '德阳市', '南充市', '宜宾市'] },
  ];

  const handleLocation = () => {
    setIsLocating(true);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          // 实际项目中应该调用反向地理编码 API 将经纬度转换为城市名
          // 这里暂时使用模拟数据
          setTimeout(() => {
            // 注意：这里应该根据 pos.coords.latitude 和 pos.coords.longitude
            // 调用地理编码服务获取真实城市，目前仅作为示例
            setLocation('北京市 海淀区');
            setIsLocating(false);
          }, 1000);
        },
        (err) => {
          console.error('定位失败:', err);
          setIsLocating(false);
          setShowLocationPicker(true);
        }
      );
    } else {
      setShowLocationPicker(true);
      setIsLocating(false);
    }
  };

  const handleManualLocation = (province: string, city: string) => {
    setLocation(`${province} ${city}`);
    setShowLocationPicker(false);
  };
  
  return (
    <div className="flex-1 w-full p-4 sm:p-8 flex flex-col">
      <div className="m-auto w-full max-w-3xl flex flex-col items-center justify-center shrink-0 py-4">
        <div className="text-center mb-10">
        <h2 className="text-4xl font-black mb-4 text-ink">📄 投喂合同给小动物们</h2>
        <p className="text-gray-custom text-base font-bold">支持 PDF、Word 文档，或直接拍照上传。系统将自动提取并加密分析文本。</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 w-full mb-10">
        <FormatCard type="pdf" icon={<FileText size={40} strokeWidth={2.5} />} label="PDF 文档" selected={selectedFormat === 'pdf'} onClick={() => setSelectedFormat('pdf')} />
        <FormatCard type="word" icon={<File size={40} strokeWidth={2.5} />} label="Word 文档" selected={selectedFormat === 'word'} onClick={() => setSelectedFormat('word')} />
        <FormatCard type="image" icon={<FileImage size={40} strokeWidth={2.5} />} label="拍照/截图" selected={selectedFormat === 'image'} onClick={() => setSelectedFormat('image')} />
      </div>

      <div
        className="w-full border-4 border-dashed border-ink rounded-3xl bg-surface p-16 flex flex-col items-center justify-center cursor-pointer hover:bg-secondary/20 transition-colors group mb-6"
        onClick={onUpload}
      >
        <div className="bg-secondary p-4 rounded-full border-4 border-ink shadow-[4px_4px_0px_var(--color-ink)] mb-6 group-hover:scale-110 transition-transform">
          <UploadCloud size={40} className="text-ink" strokeWidth={2.5} />
        </div>
        <span className="font-black text-xl mb-2 text-ink">把文件拖到这里，或者点击上传</span>
        <span className="text-gray-custom text-sm font-bold">支持 .pdf, .docx, .png, .jpg (最大 50MB)</span>
      </div>

      <div className="flex gap-4 items-center">
        <button
          onClick={handleLocation}
          disabled={isLocating || !!location}
          className={`flex items-center gap-2 px-6 py-3 rounded-2xl border-4 border-ink font-black text-sm transition-all shadow-[4px_4px_0px_var(--color-ink)] ${location ? 'bg-primary text-ink' : 'bg-surface text-ink hover:-translate-y-1 hover:shadow-[6px_6px_0px_var(--color-ink)] active:translate-y-1 active:shadow-none'}`}
        >
          {isLocating ? <Loader2 size={18} className="animate-spin" /> : <MapPin size={18} strokeWidth={3} />}
          {location ? `已定位：${location}` : '📍 开启定位 (推荐)'}
        </button>

        <button
          onClick={() => setShowLocationPicker(true)}
          className="flex items-center gap-2 px-6 py-3 rounded-2xl border-4 border-ink font-black text-sm bg-surface text-ink hover:-translate-y-1 hover:shadow-[6px_6px_0px_var(--color-ink)] active:translate-y-1 active:shadow-none transition-all shadow-[4px_4px_0px_var(--color-ink)]"
        >
          手动选择位置
        </button>

        {location && (
          <button
            onClick={() => setLocation('')}
            className="text-gray-custom hover:text-ink font-bold text-sm"
          >
            重新选择
          </button>
        )}
      </div>

      {showLocationPicker && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowLocationPicker(false)}>
          <div className="bg-surface border-4 border-ink rounded-3xl p-8 max-w-2xl w-full mx-4 shadow-[8px_8px_0px_var(--color-ink)] max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-2xl font-black mb-6 text-ink">选择您的位置</h3>
            <div className="space-y-4">
              {cities.map((item) => (
                <div key={item.province} className="border-2 border-ink rounded-2xl p-4">
                  <h4 className="font-black text-lg mb-3 text-ink">{item.province}</h4>
                  <div className="grid grid-cols-3 gap-2">
                    {item.cities.map((city) => (
                      <button
                        key={city}
                        onClick={() => handleManualLocation(item.province, city)}
                        className="px-4 py-2 rounded-xl border-2 border-ink bg-white hover:bg-primary font-bold text-sm transition-colors"
                      >
                        {city}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={() => setShowLocationPicker(false)}
              className="mt-6 w-full px-6 py-3 rounded-2xl border-4 border-ink font-black bg-gray-200 hover:bg-gray-300 transition-colors shadow-[4px_4px_0px_var(--color-ink)]"
            >
              取消
            </button>
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

const AnalysisView = ({ onComplete, theme }: { onComplete: () => void, theme: string }) => {
  const [progress, setProgress] = useState(0);
  const [currentAgentType, setCurrentAgentType] = useState<'owl'|'dog'|'beaver'|'cat'>('owl');
  const [actionText, setActionText] = useState('正在逐字阅读合同...');

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(interval);
          setTimeout(onComplete, 500);
          return 100;
        }
        if (p === 25) { setCurrentAgentType('dog'); setActionText('正在狂翻《民法典》...'); }
        if (p === 50) { setCurrentAgentType('beaver'); setActionText('正在疯狂敲算盘...'); }
        if (p === 75) { setCurrentAgentType('cat'); setActionText('正在排版避坑指南...'); }
        return p + 1;
      });
    }, 40);
    return () => clearInterval(interval);
  }, [onComplete, theme]);

  const agentNames: Record<string, string> = { owl: '猫头鹰解析师', dog: '猎犬检索师', beaver: '海狸计算师', cat: '橘猫报告师' };

  return (
    <div className="flex-1 w-full p-4 sm:p-8 flex flex-col">
      <div className="m-auto w-full max-w-md flex flex-col items-center justify-center shrink-0 py-4">
        <div className="text-6xl mb-6 animate-bounce"><AnimalIcon type={currentAgentType} theme={theme} /></div>
      <h2 className="text-2xl font-black mb-2 text-ink">{agentNames[currentAgentType]}</h2>
      <p className="text-sm font-bold text-accent mb-8">{actionText}</p>
      
      <div className="w-full h-6 bg-surface border-4 border-ink rounded-full overflow-hidden shadow-[4px_4px_0px_var(--color-ink)]">
        <div className="h-full bg-primary transition-all duration-75 relative" style={{ width: `${progress}%` }}>
          <div className="absolute inset-0 bg-surface/20 w-full" style={{ backgroundImage: 'linear-gradient(45deg, rgba(255,255,255,0.2) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.2) 75%, transparent 75%, transparent)', backgroundSize: '1rem 1rem' }}></div>
        </div>
      </div>
      <div className="w-full flex justify-between mt-4 text-sm font-black text-ink">
        <span>进度 {progress}%</span>
        <span>加油干活中 💦</span>
      </div>
      </div>
    </div>
  );
};

const FileUploadView = ({
  onUploadComplete,
  location,
  setLocation,
  privacyRedaction,
  burnAfterReading,
}: {
  onUploadComplete: (contractId: string, file: File) => void;
  location: string | null;
  setLocation: (loc: string) => void;
  privacyRedaction: boolean;
  burnAfterReading: boolean;
}) => {
  const [selectedFormat, setSelectedFormat] = useState<UploadTargetFormat>('all');
  const [isLocating, setIsLocating] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showLocationPicker, setShowLocationPicker] = useState(false);
  const [cityData, setCityData] = useState<Array<{ name: string; children: Array<{ name: string }> }>>([]);
  const [isLoadingCities, setIsLoadingCities] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 加载城市数据
  useEffect(() => {
    const loadCityData = async () => {
      try {
        setIsLoadingCities(true);
        const response = await fetch('https://unpkg.com/province-city-china/dist/level.json');
        const data = await response.json();
        // 只保留省和市级数据，过滤掉区县
        const simplified = data.map((province: any) => ({
          name: province.name,
          children: province.children?.map((city: any) => ({
            name: city.name
          })) || []
        }));
        setCityData(simplified);
      } catch (error) {
        console.error('加载城市数据失败:', error);
        // 使用备用数据
        setCityData([
          { name: '北京市', children: [{ name: '东城区' }, { name: '西城区' }, { name: '朝阳区' }, { name: '海淀区' }] },
          { name: '上海市', children: [{ name: '黄浦区' }, { name: '徐汇区' }, { name: '浦东新区' }] },
          { name: '广东省', children: [{ name: '广州市' }, { name: '深圳市' }, { name: '珠海市' }] },
        ]);
      } finally {
        setIsLoadingCities(false);
      }
    };
    loadCityData();
  }, []);

  const handleLocation = () => {
    setIsLocating(true);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        () => {
          setTimeout(() => {
            setLocation('北京市 海淀区');
            setIsLocating(false);
          }, 1000);
        },
        () => {
          setIsLocating(false);
          setShowLocationPicker(true);
        }
      );
    } else {
      setIsLocating(false);
      setShowLocationPicker(true);
    }
  };

  const handleManualLocation = (province: string, city: string) => {
    setLocation(`${province} ${city}`);
    setShowLocationPicker(false);
  };

  const handleFormatSelect = (format: UploadFormat) => {
    setSelectedFormat((current) => (current === format ? 'all' : format));
    setUploadError(null);
  };

  const handleUploadRequest = () => {
    if (isUploading) {
      return;
    }

    setUploadError(null);
    openNativeFileDialog(fileInputRef.current);
  };

  const handleFilesSelected = async (
    fileList: FileList | File[] | null | undefined
  ) => {
    if (isUploading) {
      return;
    }

    const files = fileList ? Array.from(fileList) : [];
    const validation = validateUploadSelection(files, selectedFormat);
    if (!validation.ok || files.length === 0) {
      setUploadError(validation.error ?? '上传文件不符合要求，请重新选择。');
      return;
    }

    const [file] = files;
    const detectedFormat = detectUploadFormat(file);
    if (detectedFormat) {
      setSelectedFormat(detectedFormat);
    }

    setUploadError(null);
    setIsUploading(true);

    try {
      const contractId = await uploadContract(file, location ?? undefined, {
        privacyRedaction,
        burnAfterReading,
      });
      onUploadComplete(contractId, file);
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : '上传失败，请稍后重试。'
      );
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFileInputChange = async (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    await handleFilesSelected(event.target.files);
  };

  const handleDrop = async (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    await handleFilesSelected(event.dataTransfer.files);
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (!isUploading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
      return;
    }

    setIsDragging(false);
  };

  const handleDropzoneKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Enter' && event.key !== ' ') {
      return;
    }

    event.preventDefault();
    handleUploadRequest();
  };

  return (
    <div className="flex-1 w-full p-4 sm:p-8 flex flex-col">
      <div className="m-auto w-full max-w-3xl flex flex-col items-center justify-center shrink-0 py-4">
        <div className="text-center mb-10">
          <h2 className="text-4xl font-black mb-4 text-ink">上传合同给小动物们</h2>
          <p className="text-gray-custom text-base font-bold">
            支持拖拽上传或点击选择文件，系统会自动校验格式并开始分析。
          </p>
        </div>

        {privacyRedaction && (
          <div className="w-full mb-6 rounded-2xl border-4 border-ink bg-secondary/30 px-4 py-3 text-sm font-black text-ink shadow-[4px_4px_0px_var(--color-ink)]">
            隐私消除已开启：上传后的合同会先自动脱敏，再进入分析流程。
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 w-full mb-10">
          <FormatCard
            type="pdf"
            icon={<FileText size={40} strokeWidth={2.5} />}
            label="PDF 文档"
            selected={selectedFormat === 'pdf'}
            onClick={() => handleFormatSelect('pdf')}
          />
          <FormatCard
            type="word"
            icon={<File size={40} strokeWidth={2.5} />}
            label="Word 文档"
            selected={selectedFormat === 'word'}
            onClick={() => handleFormatSelect('word')}
          />
          <FormatCard
            type="image"
            icon={<FileImage size={40} strokeWidth={2.5} />}
            label="拍照/截图"
            selected={selectedFormat === 'image'}
            onClick={() => handleFormatSelect('image')}
          />
        </div>

        <div
          className={`w-full border-4 border-dashed border-ink rounded-3xl bg-surface p-16 flex flex-col items-center justify-center transition-colors group mb-4 ${
            isUploading
              ? 'cursor-wait opacity-80'
              : 'cursor-pointer hover:bg-secondary/20'
          } ${isDragging ? 'bg-secondary/20' : ''}`}
          onClick={handleUploadRequest}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onKeyDown={handleDropzoneKeyDown}
          role="button"
          tabIndex={isUploading ? -1 : 0}
          aria-disabled={isUploading}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={getUploadAccept(selectedFormat)}
            className="hidden"
            onChange={handleFileInputChange}
            disabled={isUploading}
          />
          <div className="bg-secondary p-4 rounded-full border-4 border-ink shadow-[4px_4px_0px_var(--color-ink)] mb-6 group-hover:scale-110 transition-transform">
            {isUploading ? (
              <Loader2 size={40} className="text-ink animate-spin" strokeWidth={2.5} />
            ) : (
              <UploadCloud size={40} className="text-ink" strokeWidth={2.5} />
            )}
          </div>
          <span className="font-black text-xl mb-2 text-ink">
            {isUploading
              ? '正在上传文件并准备分析...'
              : '把文件拖到这里，或点击选择文件'}
          </span>
          <span className="text-gray-custom text-sm font-bold">
            {getUploadHint(selectedFormat)}
          </span>
          <span className="text-gray-custom/80 text-xs font-bold mt-3">
            一次仅支持 1 个文件，点击上方卡片可临时限制上传格式
          </span>
        </div>

        {uploadError && (
          <div className="w-full mb-6 bg-accent/10 border-2 border-accent rounded-2xl px-4 py-3 flex items-start gap-3 text-accent">
            <AlertTriangle size={18} strokeWidth={2.5} className="mt-0.5 shrink-0" />
            <span className="text-sm font-black">{uploadError}</span>
          </div>
        )}

        <div className="flex gap-4 items-center">
          <button
            onClick={handleLocation}
            disabled={isLocating || !!location}
            className={`flex items-center gap-2 px-6 py-3 rounded-2xl border-4 border-ink font-black text-sm transition-all shadow-[4px_4px_0px_var(--color-ink)] ${
              location
                ? 'bg-primary text-ink'
                : 'bg-surface text-ink hover:-translate-y-1 hover:shadow-[6px_6px_0px_var(--color-ink)] active:translate-y-1 active:shadow-none'
            }`}
          >
            {isLocating ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <MapPin size={18} strokeWidth={3} />
            )}
            {location ? `已定位：${location}` : '开启定位（推荐） - 获取当地租房政策'}
          </button>

          <button
            onClick={() => setShowLocationPicker(true)}
            className="flex items-center gap-2 px-6 py-3 rounded-2xl border-4 border-ink font-black text-sm bg-surface text-ink hover:-translate-y-1 hover:shadow-[6px_6px_0px_var(--color-ink)] active:translate-y-1 active:shadow-none transition-all shadow-[4px_4px_0px_var(--color-ink)]"
          >
            手动选择位置
          </button>

          {location && (
            <button
              onClick={() => setLocation('')}
              className="text-gray-custom hover:text-ink font-bold text-sm"
            >
              重新选择
            </button>
          )}
        </div>

        {showLocationPicker && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowLocationPicker(false)}>
            <div className="bg-surface border-4 border-ink rounded-3xl p-8 max-w-4xl w-full mx-4 shadow-[8px_8px_0px_var(--color-ink)] max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-2xl font-black mb-6 text-ink">选择您的位置</h3>
              {isLoadingCities ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 size={40} className="animate-spin text-ink" />
                  <span className="ml-4 font-bold text-ink">正在加载城市数据...</span>
                </div>
              ) : (
                <div className="space-y-4">
                  {cityData.map((province) => (
                    <div key={province.name} className="border-2 border-ink rounded-2xl p-4">
                      <h4 className="font-black text-lg mb-3 text-ink">{province.name}</h4>
                      <div className="grid grid-cols-4 gap-2">
                        {province.children.map((city) => (
                          <button
                            key={city.name}
                            onClick={() => handleManualLocation(province.name, city.name)}
                            className="px-3 py-2 rounded-xl border-2 border-ink bg-white hover:bg-primary font-bold text-sm transition-colors truncate"
                            title={city.name}
                          >
                            {city.name}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <button
                onClick={() => setShowLocationPicker(false)}
                className="mt-6 w-full px-6 py-3 rounded-2xl border-4 border-ink font-black bg-gray-200 hover:bg-gray-300 transition-colors shadow-[4px_4px_0px_var(--color-ink)]"
              >
                取消
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const LiveAnalysisView = ({
  contractId,
  fileName,
  onComplete,
  onRetry,
  theme,
}: {
  contractId: string | null;
  fileName: string | null;
  onComplete: (report: AnalysisReport) => void;
  onRetry: () => void;
  theme: string;
}) => {
  const [progress, setProgress] = useState(5);
  const [currentAgentType, setCurrentAgentType] = useState<'owl' | 'dog' | 'beaver' | 'cat'>('owl');
  const [actionText, setActionText] = useState('正在准备分析任务...');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!contractId) {
      setErrorMessage('缺少合同信息，请重新上传文件。');
      return;
    }

    let isCancelled = false;
    let completionTimer: ReturnType<typeof setTimeout> | null = null;

    const applyStage = (eventType: AnalysisEvent['type']) => {
      if (eventType === 'analysis_started') {
        setProgress(12);
        setCurrentAgentType('owl');
        setActionText('正在准备分析任务...');
      } else if (eventType === 'owl_analysis') {
        setProgress(38);
        setCurrentAgentType('owl');
        setActionText('猫头鹰正在逐条解析合同条款...');
      } else if (eventType === 'dog_retrieval') {
        setProgress(62);
        setCurrentAgentType('dog');
        setActionText('猎犬正在检索相关法条和案例...');
      } else if (eventType === 'beaver_calculation') {
        setProgress(84);
        setCurrentAgentType('beaver');
        setActionText('海狸正在核算押金和费用...');
      } else if (eventType === 'cat_report') {
        setProgress(95);
        setCurrentAgentType('cat');
        setActionText('橘猫正在整理最终风险报告...');
      } else if (eventType === 'analysis_complete') {
        setProgress(100);
        setCurrentAgentType('cat');
        setActionText('分析完成，正在打开结果...');
      }
    };

    const eventSource = analyzeContract(
      contractId,
      async (event) => {
        if (isCancelled) {
          return;
        }

        if (event.type === 'error') {
          setErrorMessage(event.message ?? '合同分析失败，请稍后重试。');
          eventSource.close();
          return;
        }

        applyStage(event.type);

        if (event.type === 'analysis_complete') {
          try {
            const report = await getReport(contractId);
            if (isCancelled) {
              return;
            }

            // 添加调试日志
            console.log('[前端] 获取到分析报告:', {
              contractId,
              riskItemsCount: report.risk_items?.length ?? 0,
              highRiskCount: report.risk_items?.filter(item => item.risk_level === 'high').length ?? 0,
              mediumRiskCount: report.risk_items?.filter(item => item.risk_level === 'medium').length ?? 0,
              lowRiskCount: report.risk_items?.filter(item => item.risk_level === 'low').length ?? 0,
              entities: report.entities,
            });

            completionTimer = setTimeout(() => {
              onComplete(report);
            }, 400);
          } catch (error) {
            setErrorMessage(
              error instanceof Error ? error.message : '获取分析报告失败，请稍后重试。'
            );
          } finally {
            eventSource.close();
          }
        }
      },
      (error) => {
        if (isCancelled) {
          return;
        }

        setErrorMessage(error.message || '合同分析失败，请稍后重试。');
      }
    );

    return () => {
      isCancelled = true;
      if (completionTimer) {
        clearTimeout(completionTimer);
      }
      eventSource.close();
    };
  }, [contractId, onComplete]);

  const agentNames: Record<string, string> = {
    owl: '猫头鹰分析师',
    dog: '猎犬检索师',
    beaver: '海狸计算师',
    cat: '橘猫报告师',
  };

  if (errorMessage) {
    return (
      <div className="flex-1 w-full p-4 sm:p-8 flex flex-col">
        <div className="m-auto w-full max-w-md flex flex-col items-center justify-center shrink-0 py-4 text-center">
          <div className="mb-6">
            <AlertTriangle size={56} className="text-accent" strokeWidth={2.5} />
          </div>
          <h2 className="text-2xl font-black mb-3 text-ink">分析中断了</h2>
          <p className="text-sm font-bold text-gray-custom mb-6">{errorMessage}</p>
          <button
            onClick={onRetry}
            className="px-6 py-3 rounded-2xl border-4 border-ink bg-primary font-black text-ink shadow-[4px_4px_0px_var(--color-ink)] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all"
          >
            返回重新上传
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full p-4 sm:p-8 flex flex-col">
      <div className="m-auto w-full max-w-md flex flex-col items-center justify-center shrink-0 py-4">
        <div className="text-6xl mb-6 animate-bounce">
          <AnimalIcon type={currentAgentType} theme={theme} />
        </div>
        <h2 className="text-2xl font-black mb-2 text-ink">{agentNames[currentAgentType]}</h2>
        <p className="text-sm font-bold text-accent mb-2">{actionText}</p>
        {fileName && (
          <p className="text-xs font-bold text-gray-custom mb-6">当前文件：{fileName}</p>
        )}

        <div className="w-full h-6 bg-surface border-4 border-ink rounded-full overflow-hidden shadow-[4px_4px_0px_var(--color-ink)]">
          <div
            className="h-full bg-primary transition-all duration-300 relative"
            style={{ width: `${progress}%` }}
          >
            <div
              className="absolute inset-0 bg-surface/20 w-full"
              style={{
                backgroundImage:
                  'linear-gradient(45deg, rgba(255,255,255,0.2) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.2) 75%, transparent 75%, transparent)',
                backgroundSize: '1rem 1rem',
              }}
            ></div>
          </div>
        </div>
        <div className="w-full flex justify-between mt-4 text-sm font-black text-ink">
          <span>进度 {progress}%</span>
          <span>真实分析进行中</span>
        </div>
      </div>
    </div>
  );
};

// --- New Workspace View (3-Pane Layout) ---
const WorkspaceView = ({ onLogout, location, onNewChat, settings, setSettings, uploadedFileName, analysisReport }: { onLogout: () => void, location: string | null, onNewChat: () => void, settings: any, setSettings: any, uploadedFileName: string | null, analysisReport: AnalysisReport | null }) => {
  const [activeNav, setActiveNav] = useState<'chat' | 'history' | 'preferences' | 'settings'>('chat');
  const [activeAgent, setActiveAgent] = useState<'owl' | 'dog' | 'beaver'>('owl');
  const [chatInput, setChatInput] = useState('');
  const [docTitle, setDocTitle] = useState('04_租金贷风险合同.docx');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [showNewChatModal, setShowNewChatModal] = useState(false);

  useEffect(() => {
    if (uploadedFileName) {
      setDocTitle(uploadedFileName);
    }
  }, [uploadedFileName]);

  const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 25, 200));
  const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 25, 50));

  // 修复：移除默认值，如果没有分析报告则显示 0
  const highRiskCount = analysisReport?.risk_items.filter((item) => item.risk_level === 'high').length ?? 0;
  const mediumRiskCount = analysisReport?.risk_items.filter((item) => item.risk_level === 'medium').length ?? 0;
  const lowRiskCount = analysisReport?.risk_items.filter((item) => item.risk_level === 'low').length ?? 0;
  const totalRiskCount = highRiskCount + mediumRiskCount + lowRiskCount;

  // 添加调试日志
  useEffect(() => {
    console.log('[WorkspaceView] 分析报告更新:', {
      hasReport: !!analysisReport,
      riskItemsCount: analysisReport?.risk_items?.length ?? 0,
      highRiskCount,
      mediumRiskCount,
      lowRiskCount,
      totalRiskCount,
      lessor: analysisReport?.entities?.lessor,
      lessee: analysisReport?.entities?.lessee,
      monthlyRent: analysisReport?.entities?.monthly_rent,
      deposit: analysisReport?.entities?.deposit,
    });
  }, [analysisReport, highRiskCount, mediumRiskCount, lowRiskCount, totalRiskCount]);

  const workspaceStatusText = analysisReport ? '已加载真实分析结果' : '已加载 智审内核已就绪';

  const agents: Record<string, any> = {
    owl: { name: '猫头鹰解析师', role: '条款拆解与霸王条款识别', color: 'bg-accent' },
    dog: { name: '猎犬检索师', role: '法律法规与案例匹配', color: 'bg-primary' },
    beaver: { name: '海狸计算师', role: '水电押金与费用核算', color: 'bg-secondary' },
  };

  return (
    <div className="flex-1 flex overflow-hidden border-4 border-ink rounded-3xl shadow-[8px_8px_0px_var(--color-ink)] bg-surface m-4 sm:m-8 mt-0">
      
      {/* 1. Left Sidebar (Navigation) */}
      <aside className="w-20 sm:w-24 border-r-4 border-ink bg-paper flex flex-col items-center py-6 shrink-0 z-10">
        <div className="w-12 h-12 bg-secondary border-4 border-ink rounded-2xl flex items-center justify-center text-2xl mb-8 shadow-[2px_2px_0px_var(--color-ink)] transform -rotate-6">
          🐾
        </div>
        
        <nav className="flex-1 flex flex-col gap-6 w-full px-2 sm:px-4">
          <button 
            onClick={() => setActiveNav('chat')}
            className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-all ${activeNav === 'chat' ? 'bg-ink text-surface shadow-[2px_2px_0px_var(--color-ink)] translate-x-1' : 'text-gray-custom hover:bg-ink/10'}`}
          >
            <MessageCircle size={24} strokeWidth={2.5} />
            <span className="text-[10px] font-black">实时对话</span>
          </button>
          <button 
            onClick={() => setActiveNav('history')}
            className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-all ${activeNav === 'history' ? 'bg-ink text-surface shadow-[2px_2px_0px_var(--color-ink)] translate-x-1' : 'text-gray-custom hover:bg-ink/10'}`}
          >
            <History size={24} strokeWidth={2.5} />
            <span className="text-[10px] font-black">审查历史</span>
          </button>
          <button 
            onClick={() => setActiveNav('preferences')}
            className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-all ${activeNav === 'preferences' ? 'bg-ink text-surface shadow-[2px_2px_0px_var(--color-ink)] translate-x-1' : 'text-gray-custom hover:bg-ink/10'}`}
          >
            <User size={24} strokeWidth={2.5} />
            <span className="text-[10px] font-black">个人偏好</span>
          </button>
          <button 
            onClick={() => setActiveNav('settings')}
            className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-all ${activeNav === 'settings' ? 'bg-ink text-surface shadow-[2px_2px_0px_var(--color-ink)] translate-x-1' : 'text-gray-custom hover:bg-ink/10'}`}
          >
            <Settings size={24} strokeWidth={2.5} />
            <span className="text-[10px] font-black">系统设置</span>
          </button>
        </nav>

        <button onClick={onLogout} className="mt-auto flex flex-col items-center gap-1 p-2 text-accent hover:bg-accent/10 rounded-xl transition-colors w-full">
          <LogOut size={24} strokeWidth={2.5} />
          <span className="text-[10px] font-black">退出登录</span>
        </button>
      </aside>

      {/* 2. Middle Panel (Chat & Risks / History) */}
      <section className="w-80 sm:w-96 border-r-4 border-ink bg-surface flex flex-col shrink-0 z-0 relative">
        {activeNav === 'chat' ? (
          <>
            {/* Agent Selector Header */}
            <div className="p-4 border-b-4 border-ink bg-paper shrink-0">
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                {(Object.keys(agents) as Array<keyof typeof agents>).map(key => (
                  <button 
                    key={key}
                    onClick={() => setActiveAgent(key)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl border-2 border-ink font-black text-sm whitespace-nowrap transition-all ${activeAgent === key ? `${agents[key].color} shadow-[2px_2px_0px_var(--color-ink)] scale-105 text-[#2D3142]` : 'bg-surface text-gray-custom hover:bg-ink/5'}`}
                  >
                    <span><AnimalIcon type={key} theme={settings.theme} /></span> {agents[key].name}
                  </button>
                ))}
              </div>
              <div className="mt-2 flex items-center gap-2 text-xs font-bold text-ink/70">
                <CheckCircle2 size={14} className="text-primary" /> 审查完成 · {agents[activeAgent].role}
              </div>
            </div>

            {/* Risk Cards List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-surface-alt">
              {activeAgent === 'owl' && (
                <>
                  <div className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-2 bg-accent"></div>
                    <div className="flex justify-between items-start mb-2 mt-1">
                      <h3 className="font-black text-ink text-lg">提前退租违约金条款</h3>
                      <span className="bg-accent text-white px-2 py-1 rounded-lg text-xs font-black border-2 border-ink">高风险</span>
                    </div>
                    <p className="text-sm font-bold text-gray-custom mb-3">
                      合同要求提前退租支付两个月租金作为违约金，标准明显偏高。
                    </p>
                    <p className="text-xs font-black text-primary mb-4 flex items-center gap-1">
                      📖 法律依据：《民法典》第585条
                    </p>
                    <div className="flex gap-2">
                      <button className="flex-1 bg-secondary border-2 border-ink rounded-xl py-2 text-xs font-black hover:bg-secondary/80 transition-colors">✨ 自动修正</button>
                      <button className="flex-1 bg-surface border-2 border-ink rounded-xl py-2 text-xs font-black hover:bg-ink/5 transition-colors">📄 查看法务意见</button>
                    </div>
                  </div>

                  <div className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-2 bg-accent"></div>
                    <div className="flex justify-between items-start mb-2 mt-1">
                      <h3 className="font-black text-ink text-lg">押金不退条款</h3>
                      <span className="bg-accent text-white px-2 py-1 rounded-lg text-xs font-black border-2 border-ink">高风险</span>
                    </div>
                    <p className="text-sm font-bold text-gray-custom mb-3">
                      “无论任何原因押金不予退还”属于典型的排除承租人权利的格式条款。
                    </p>
                    <p className="text-xs font-black text-primary mb-4 flex items-center gap-1">
                      📖 法律依据：《民法典》第497条
                    </p>
                    <div className="flex gap-2">
                      <button className="flex-1 bg-secondary border-2 border-ink rounded-xl py-2 text-xs font-black hover:bg-secondary/80 transition-colors">✨ 自动修正</button>
                    </div>
                  </div>
                </>
              )}
              {activeAgent === 'beaver' && (
                <div className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-2 bg-secondary"></div>
                  <div className="flex justify-between items-start mb-2 mt-1">
                    <h3 className="font-black text-ink text-lg">电费违规加价</h3>
                    <span className="bg-secondary text-[#2D3142] px-2 py-1 rounded-lg text-xs font-black border-2 border-ink">中风险</span>
                  </div>
                  <p className="text-sm font-bold text-gray-custom mb-3">
                    合同约定电费1.5元/度。根据<span className="text-accent font-black">{location || '当地'}</span>最新发改委规定，居民阶梯电价最高档为0.8元/度，房东涉嫌违法加价！
                  </p>
                  <div className="flex gap-2">
                    <button className="flex-1 bg-primary border-2 border-ink rounded-xl py-2 text-xs font-black hover:bg-primary/80 transition-colors">🧮 重新核算</button>
                  </div>
                </div>
              )}
              {activeAgent === 'dog' && (
                <div className="text-center p-8 text-gray-custom font-bold">
                  <div className="text-4xl mb-2">🐶</div>
                  <p>猎犬检索师暂未发现其他严重违法条款，合同整体框架合法。</p>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <div className="p-4 border-t-4 border-ink bg-surface shrink-0">
              <div className="relative">
                <textarea 
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder={`告诉 ${agents[activeAgent].name} 你的情况...`}
                  className="w-full border-4 border-ink rounded-2xl p-3 pr-12 text-sm font-bold focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all resize-none h-24 bg-paper"
                ></textarea>
                <button className="absolute right-3 bottom-3 bg-ink text-surface p-2 rounded-xl hover:scale-110 transition-transform">
                  <Send size={16} strokeWidth={3} />
                </button>
              </div>
            </div>
          </>
        ) : activeNav === 'history' ? (
          <div className="flex-1 flex flex-col bg-surface-alt">
            <div className="p-4 border-b-4 border-ink bg-paper shrink-0">
              <h2 className="text-xl font-black text-ink">审查历史</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] cursor-pointer hover:-translate-y-1 transition-transform">
                <h3 className="font-black text-ink mb-1">{docTitle}</h3>
                <p className="text-xs font-bold text-gray-custom mb-2">2024-05-12 14:30</p>
                <div className="flex gap-2">
                  <span className="bg-accent/20 text-accent px-2 py-1 rounded-lg text-[10px] font-black border-2 border-accent/30">2 处高危</span>
                  <span className="bg-primary/20 text-primary px-2 py-1 rounded-lg text-[10px] font-black border-2 border-primary/30">已优化</span>
                </div>
              </div>
              <div className="bg-surface border-4 border-ink rounded-2xl p-4 shadow-[4px_4px_0px_var(--color-ink)] cursor-pointer hover:-translate-y-1 transition-transform opacity-70">
                <h3 className="font-black text-ink mb-1">自如合租合同_张三.pdf</h3>
                <p className="text-xs font-bold text-gray-custom mb-2">2024-03-08 09:15</p>
                <div className="flex gap-2">
                  <span className="bg-secondary/20 text-ink px-2 py-1 rounded-lg text-[10px] font-black border-2 border-secondary/50">0 处高危</span>
                </div>
              </div>
            </div>
          </div>
        ) : activeNav === 'preferences' ? (
          <div className="flex-1 flex flex-col bg-surface-alt min-h-0">
            <div className="p-4 border-b-4 border-ink bg-paper shrink-0">
              <h2 className="text-xl font-black text-ink">个人偏好</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4 sm:p-8">
              <div className="max-w-2xl mx-auto space-y-6">
                <div className="bg-surface border-4 border-ink rounded-2xl p-6 shadow-[4px_4px_0px_var(--color-ink)]">
                  <h3 className="text-lg font-black text-ink mb-4 flex items-center gap-2">
                    <User size={20} className="text-primary" /> 🐾 告诉小动物们你的情况
                  </h3>
                  <p className="text-sm font-bold text-gray-custom mb-6">
                    悄悄告诉我们你的租房底线，猫头鹰和海狸在看合同时会帮你盯紧这些坑哦！
                  </p>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-black text-ink mb-2">我的身份标签</label>
                      <select 
                        value={settings.identity}
                        onChange={(e) => setSettings({...settings, identity: e.target.value})}
                        className="w-full border-4 border-ink rounded-xl p-3 font-bold bg-paper focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all"
                      >
                        <option>在校大学生</option>
                        <option>应届毕业生</option>
                        <option>考研党</option>
                        <option>实习生</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-black text-ink mb-2">心理预期 (预算、付款方式等)</label>
                      <input 
                        type="text"
                        value={settings.budget}
                        onChange={(e) => setSettings({...settings, budget: e.target.value})}
                        placeholder="例如：预算2000内，希望押一付一..."
                        className="w-full border-4 border-ink rounded-xl p-3 font-bold bg-paper focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-black text-ink mb-2">核心注意事项 (绝对不能接受的坑)</label>
                      <textarea 
                        value={settings.dealbreakers}
                        onChange={(e) => setSettings({...settings, dealbreakers: e.target.value})}
                        placeholder="例如：不能接受二房东、必须能办居住证、不能有隐藏的物业费..."
                        className="w-full border-4 border-ink rounded-xl p-3 font-bold bg-paper focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all h-24 resize-none"
                      />
                    </div>

                    <button 
                      onClick={() => alert('设置已保存！AI 将在下次审查时参考这些偏好。')}
                      className="w-full py-3 mt-4 rounded-xl border-4 border-ink bg-primary font-black text-ink shadow-[4px_4px_0px_var(--color-ink)] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all flex items-center justify-center gap-2"
                    >
                      <CheckCircle2 size={18} strokeWidth={3} /> 保存个性化偏好
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col bg-surface-alt min-h-0">
            <div className="p-4 border-b-4 border-ink bg-paper shrink-0">
              <h2 className="text-xl font-black text-ink">系统设置</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4 sm:p-8">
              <div className="max-w-2xl mx-auto space-y-6">
                <div className="bg-surface border-4 border-ink rounded-2xl p-6 shadow-[4px_4px_0px_var(--color-ink)]">
                  <h3 className="text-lg font-black text-ink mb-6 flex items-center gap-2">
                    <Settings size={20} className="text-primary" /> 基础设置
                  </h3>
                  
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-black text-ink">桌面通知</div>
                        <div className="text-xs font-bold text-gray-custom mt-1">小动物们审查完毕后，第一时间通知你</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input 
                          type="checkbox" 
                          className="sr-only peer" 
                          checked={settings.notifications}
                          onChange={(e) => setSettings({...settings, notifications: e.target.checked})}
                        />
                        <div className="w-11 h-6 bg-ink/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-surface after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-ink/20 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border-2 border-ink"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-black text-ink">合同阅后即焚</div>
                        <div className="text-xs font-bold text-gray-custom mt-1">退出登录后自动销毁当前合同记录，不留痕迹（保留偏好设置）</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input 
                          type="checkbox" 
                          className="sr-only peer" 
                          checked={settings.burnAfterReading}
                          onChange={(e) => setSettings({...settings, burnAfterReading: e.target.checked})}
                        />
                        <div className="w-11 h-6 bg-ink/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-surface after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-ink/20 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border-2 border-ink"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-black text-ink">界面主题</div>
                        <div className="text-xs font-bold text-gray-custom mt-1">选择你喜欢的颜色风格</div>
                      </div>
                      <select 
                        className="border-4 border-ink rounded-xl p-2 font-bold bg-paper focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all text-sm text-ink"
                        value={settings.theme}
                        onChange={(e) => setSettings({...settings, theme: e.target.value})}
                      >
                        <option value="light">浅色模式</option>
                        <option value="dark">深色模式</option>
                      </select>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-black text-ink">字体大小</div>
                        <div className="text-xs font-bold text-gray-custom mt-1">调整合同阅读区的文字大小</div>
                      </div>
                      <select 
                        className="border-4 border-ink rounded-xl p-2 font-bold bg-paper focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all text-sm text-ink"
                        value={settings.fontSize}
                        onChange={(e) => setSettings({...settings, fontSize: e.target.value})}
                      >
                        <option value="standard">标准</option>
                        <option value="large">偏大</option>
                        <option value="xlarge">特大</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* 3. Right Panel (Document Viewer) */}
      <section className="flex-1 flex flex-col bg-surface overflow-hidden relative">
        {/* Toolbar */}
        <div className="h-16 border-b-4 border-ink bg-paper flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-2 max-w-[200px] sm:max-w-md w-full">
            {isEditingTitle ? (
              <input
                type="text"
                value={docTitle}
                onChange={(e) => setDocTitle(e.target.value)}
                onBlur={() => setIsEditingTitle(false)}
                onKeyDown={(e) => e.key === 'Enter' && setIsEditingTitle(false)}
                autoFocus
                className="font-black text-ink text-sm sm:text-base border-b-2 border-ink bg-transparent focus:outline-none w-full"
              />
            ) : (
              <>
                <span className="font-black text-ink text-sm sm:text-base truncate" title={docTitle}>
                  {docTitle}
                </span>
                <button onClick={() => setIsEditingTitle(true)} className="text-gray-custom hover:text-ink transition-colors shrink-0">
                  <Edit2 size={14} strokeWidth={3} />
                </button>
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            {location && (
              <div className="hidden sm:flex items-center gap-1 bg-primary/20 text-ink border-2 border-ink px-3 py-1.5 rounded-xl text-xs font-black shadow-[2px_2px_0px_var(--color-ink)]">
                <MapPin size={14} strokeWidth={3} /> {location}
              </div>
            )}
            <button 
              onClick={() => setShowNewChatModal(true)}
              className="hidden sm:flex items-center gap-2 bg-surface border-2 border-ink px-3 py-1.5 rounded-xl text-xs font-black shadow-[2px_2px_0px_var(--color-ink)] hover:-translate-y-0.5 transition-all"
            >
              <Plus size={14} strokeWidth={3} /> 新建对话
            </button>
            <div className="flex items-center border-2 border-ink rounded-xl bg-surface overflow-hidden shadow-[2px_2px_0px_var(--color-ink)]">
              <button onClick={handleZoomOut} className="px-2 py-1.5 hover:bg-ink/10 transition-colors border-r-2 border-ink"><ZoomOut size={14} strokeWidth={3} /></button>
              <span className="px-3 py-1.5 text-xs font-black w-14 text-center">{zoomLevel}%</span>
              <button onClick={handleZoomIn} className="px-2 py-1.5 hover:bg-ink/10 transition-colors border-l-2 border-ink"><ZoomIn size={14} strokeWidth={3} /></button>
            </div>
            <div className="relative">
              <button 
                onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                className="bg-primary text-ink border-2 border-ink p-1.5 rounded-xl shadow-[2px_2px_0px_var(--color-ink)] hover:-translate-y-0.5 transition-all flex items-center gap-1"
              >
                <Download size={16} strokeWidth={3} />
              </button>
              
              <AnimatePresence>
                {showDownloadMenu && (
                  <motion.div 
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-full mt-2 w-40 bg-surface border-4 border-ink rounded-2xl shadow-[4px_4px_0px_var(--color-ink)] overflow-hidden z-50 flex flex-col"
                  >
                    <button 
                      onClick={() => { setShowDownloadMenu(false); alert('正在生成修改后的纯净版合同...'); }}
                      className="flex items-center gap-2 px-4 py-3 text-sm font-black text-ink hover:bg-secondary/20 border-b-2 border-ink/10 transition-colors text-left"
                    >
                      <FileCheck size={16} className="shrink-0" /> 纯净修改版
                    </button>
                    <button 
                      onClick={() => { setShowDownloadMenu(false); alert('正在生成带AI批注的审查报告版合同...'); }}
                      className="flex items-center gap-2 px-4 py-3 text-sm font-black text-ink hover:bg-accent/20 transition-colors text-left"
                    >
                      <FileText size={16} className="shrink-0" /> AI 批注版
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>

        {/* Document Content */}
        <div className="flex-1 overflow-auto p-8 sm:p-12 bg-surface-alt flex justify-center">
          <div className="min-w-max min-h-max">
            <div 
              className="w-[800px] bg-surface border-2 border-ink/20 shadow-lg p-10 transition-transform duration-300 origin-top"
              style={{ transform: `scale(${zoomLevel / 100})` }}
            >
              <h2 className="text-2xl font-black mb-8 text-center text-ink">房屋租赁合同</h2>
            
            <div className={`space-y-6 leading-loose text-ink/80 font-bold ${settings.fontSize === 'xlarge' ? 'text-lg' : settings.fontSize === 'large' ? 'text-base' : 'text-sm'}`}>
              <p>
                <strong>六、双方权利与义务</strong><br/>
                乙方须年付租金或通过甲方合作金融机构办理租金分期。<br/>
                如乙方选择租金分期，还款义务由乙方承担，与甲方无关。<br/>
                乙方须保持房屋及设施完好，配合甲方定期免费消杀保洁。<br/>
                <span className={`transition-colors duration-300 ${activeAgent === 'owl' ? 'bg-accent/20 border-b-4 border-accent text-accent px-1 rounded-md cursor-help' : ''}`}>
                  乙方提前退租须提前60天申请，并支付两个月租金作为违约金。
                </span>
              </p>

              <p>
                <strong>七、违约责任</strong><br/>
                如乙方租金分期还款逾期，影响乙方征信记录，由乙方自行负责。<br/>
                乙方逾期支付租金超过7天，甲方有权要求乙方支付100元/次逾期手续费。<br/>
                <span className={`transition-colors duration-300 ${activeAgent === 'owl' ? 'bg-accent/20 border-b-4 border-accent text-accent px-1 rounded-md cursor-help' : ''}`}>
                  乙方提前解约且经甲方同意的，须一次性支付剩余租期租金的30%作为违约金，并扣除全部押金。
                </span><br/>
                租金分期一旦生效，无论乙方是否入住或使用房屋，贷款本息均由乙方承担。
              </p>

              <p>
                <strong>八、其他约定</strong><br/>
                <span className={`transition-colors duration-300 ${activeAgent === 'beaver' ? 'bg-secondary/40 border-b-4 border-secondary text-ink px-1 rounded-md cursor-help' : ''}`}>
                  水费：5元/吨。电费：1.5元/度。燃气费：无燃气。
                </span><br/>
                物业费：每月180元（含每周两次公区保洁、代收快递、安保服务）。<br/>
                网络费：已接入百兆宽带，免费使用。<br/>
                中介费：无（品牌公寓）。
              </p>
            </div>
          </div>
        </div>
        </div>

        {/* Status Bar */}
        <div className="h-10 border-t-4 border-ink bg-paper flex items-center justify-between px-6 shrink-0 text-xs font-black text-gray-custom z-10">
          <div className="flex gap-4">
            <span>字数: 1,004</span>
            <span className="text-accent flex items-center gap-1"><AlertTriangle size={12} strokeWidth={3} /> {highRiskCount} 处高危</span>
            <span className="text-primary flex items-center gap-1"><AlertTriangle size={12} strokeWidth={3} /> {mediumRiskCount} 处提示</span>
          </div>
          <div className="flex items-center gap-2 text-primary">
            <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div> {workspaceStatusText}
          </div>
        </div>

        {/* New Chat Modal */}
        <AnimatePresence>
          {showNewChatModal && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm p-4"
            >
              <motion.div 
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className="bg-surface border-4 border-ink rounded-3xl p-8 max-w-sm w-full shadow-[8px_8px_0px_var(--color-ink)]"
              >
                <div className="text-4xl mb-4 text-center">✨</div>
                <h3 className="text-xl font-black text-ink mb-2 text-center">开启新合同审查？</h3>
                <p className="text-sm font-bold text-gray-custom mb-8 text-center">
                  当前合同的审查记录将自动保存在“审查历史”中。
                </p>
                <div className="flex gap-4">
                  <button 
                    onClick={() => setShowNewChatModal(false)} 
                    className="flex-1 py-3 rounded-xl border-4 border-ink font-black text-ink hover:bg-surface-alt transition-colors"
                  >
                    取消
                  </button>
                  <button 
                    onClick={() => {
                      setShowNewChatModal(false);
                      onNewChat();
                    }} 
                    className="flex-1 py-3 rounded-xl border-4 border-ink bg-primary font-black text-ink shadow-[4px_4px_0px_var(--color-ink)] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all"
                  >
                    确认新建
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </div>
  );
};

export default function App() {
  const [view, setView] = useState<'login' | 'upload' | 'analyzing' | 'workspace'>('login');
  const [contractId, setContractId] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [analysisReport, setAnalysisReport] = useState<AnalysisReport | null>(null);
  const [location, setLocation] = useState<string | null>(null);
  const [showPreferencesModal, setShowPreferencesModal] = useState(false);
  const [showSystemSettingsModal, setShowSystemSettingsModal] = useState(false);
  const [authSession, setAuthSession] = useState<Session | null>(null);
  const [authUser, setAuthUser] = useState<SupabaseUser | null>(null);
  const [authProfile, setAuthProfile] = useState<RentalProfile | null>(null);
  const [settings, setSettings] = useState({
    identity: '在校大学生',
    budget: '',
    dealbreakers: '',
    notifications: true,
    burnAfterReading: true,
    privacyRedaction: false,
    theme: 'light',
    fontSize: 'standard'
  });

  useEffect(() => {
    let active = true;

    const syncAuthState = async (session: Session | null) => {
      if (!active) return;

      setAuthSession(session);
      setAuthUser(session?.user ?? null);

      if (!session?.user) {
        setAuthProfile(null);
        setView('login');
        return;
      }

      try {
        const profile = await getRentalProfile(session.user.id);
        if (active) {
          setAuthProfile(profile);
        }
      } catch (error) {
        console.error('Failed to load rental profile:', error);
      }

      setView((prev) => (prev === 'login' ? 'upload' : prev));
    };

    getCurrentSession()
      .then(syncAuthState)
      .catch((error) => {
        console.error('Failed to restore session:', error);
      });

    const {
      data: { subscription },
    } = onAuthStateChange((_event, session) => {
      void syncAuthState(session);
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (view === 'login' || view === 'upload') {
      setShowPreferencesModal(false);
      setShowSystemSettingsModal(false);
    }
  }, [view]);

  // 强制清理：确保登录页面没有遮罩层
  useEffect(() => {
    if (view === 'login') {
      console.log('[Debug] Entering login view, clearing modals...');
      console.log('[Debug] showPreferencesModal:', showPreferencesModal);
      console.log('[Debug] showSystemSettingsModal:', showSystemSettingsModal);

      // 立即清理
      setShowPreferencesModal(false);
      setShowSystemSettingsModal(false);

      // 延迟清理，确保 AnimatePresence 的退出动画完成
      const timer = setTimeout(() => {
        setShowPreferencesModal(false);
        setShowSystemSettingsModal(false);
        console.log('[Debug] Modals cleared after delay');
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [view, showPreferencesModal, showSystemSettingsModal]);

  const handleAuthenticate = async ({
    mode,
    email,
    password,
    username,
  }: {
    mode: 'login' | 'register';
    email: string;
    password: string;
    username?: string;
  }) => {
    const result =
      mode === 'login'
        ? await loginWithPassword({ email, password })
        : await registerWithPassword({
            email,
            password,
            username: username ?? '',
          });

    setAuthSession(result.session);
    setAuthUser(result.user);
    setAuthProfile(result.profile);
    setView('upload');
  };

  const handleReturnToUpload = () => {
    setContractId(null);
    setUploadedFile(null);
    setAnalysisReport(null);
    setView('upload');
  };

  const handleUploadComplete = (nextContractId: string, file: File) => {
    setContractId(nextContractId);
    setUploadedFile(file);
    setAnalysisReport(null);
    setView('analyzing');
  };

  const handleAnalysisComplete = (report: AnalysisReport) => {
    setAnalysisReport(report);
    setView('workspace');
  };

  const handleLogout = async () => {
    try {
      await cleanupBurnAfterReading();
    } catch (error) {
      console.error('Failed to cleanup burn-after-reading contracts:', error);
    }

    try {
      await logoutFromSupabase();
    } catch (error) {
      console.error('Failed to sign out:', error);
    }
    setContractId(null);
    setUploadedFile(null);
    setAnalysisReport(null);
    setAuthSession(null);
    setAuthUser(null);
    setAuthProfile(null);
    setShowPreferencesModal(false);
    setShowSystemSettingsModal(false);
    setView('login');
  };

  return (
    <div className={`flex flex-col bg-paper text-ink font-sans selection:bg-secondary selection:text-[#2D3142] ${settings.theme === 'dark' ? 'dark' : ''} ${view === 'workspace' ? 'h-screen overflow-hidden' : 'min-h-screen overflow-y-auto'} ${view === 'login' ? 'debug-no-backdrop' : ''}`}>
      {/* Global Header (Only show outside of workspace) */}
      {view !== 'workspace' && (
        <header className="flex flex-col sm:flex-row justify-between items-center border-b-4 border-ink pb-4 mb-8 shrink-0 gap-4 bg-surface p-4 mx-4 sm:mx-8 mt-4 sm:mt-8 rounded-2xl shadow-[4px_4px_0px_var(--color-ink)]">
          <div 
            className="text-2xl font-black flex items-center gap-2 text-ink cursor-pointer hover:scale-105 transition-transform"
            onClick={() => (view === 'login' ? setView('login') : handleReturnToUpload())}
          >
            <div className="bg-secondary p-2 rounded-xl border-2 border-ink transform -rotate-6">🏠</div>
            租房避坑局
          </div>
          <div className="flex items-center gap-4">
            {view !== 'login' && view !== 'upload' && (
              <button 
                onClick={handleReturnToUpload}
                className="hidden sm:flex items-center gap-2 px-4 py-2 bg-surface border-2 border-ink rounded-xl font-black text-sm shadow-[2px_2px_0px_var(--color-ink)] hover:-translate-y-0.5 hover:shadow-[4px_4px_0px_var(--color-ink)] active:translate-y-0.5 active:shadow-none transition-all"
              >
                🏠 返回首页
              </button>
            )}
            <div className="text-sm font-bold text-gray-custom hidden sm:block text-right bg-paper px-4 py-2 rounded-xl border-2 border-ink/20">
              多智能体核心引擎 v2.0<br />
              <span className="text-accent">基于大模型驱动的青年权益保护工具</span>
            </div>
            {view !== 'login' && (
              <>
                <button
                  onClick={() => setShowSystemSettingsModal(true)}
                  className="flex items-center gap-2 bg-surface border-2 border-ink px-3 py-2 rounded-xl text-sm font-black shadow-[2px_2px_0px_var(--color-ink)] hover:-translate-y-0.5 hover:bg-surface-alt transition-all shrink-0"
                >
                  <Settings size={16} strokeWidth={3} /> 系统设置
                </button>
                <button 
                  onClick={() => setShowPreferencesModal(true)}
                  className="flex items-center gap-2 bg-surface border-2 border-ink px-3 py-2 rounded-xl text-sm font-black shadow-[2px_2px_0px_var(--color-ink)] hover:-translate-y-0.5 hover:bg-surface-alt transition-all shrink-0"
                >
                  <User size={16} strokeWidth={3} /> 个人偏好
                </button>
                <button 
                  onClick={handleLogout}
                  className="flex items-center gap-2 bg-surface border-2 border-ink px-3 py-2 rounded-xl text-sm font-black shadow-[2px_2px_0px_var(--color-ink)] hover:-translate-y-0.5 hover:bg-surface-alt transition-all shrink-0"
                >
                  <LogOut size={16} strokeWidth={3} /> 退出
                </button>
              </>
            )}
          </div>
        </header>
      )}

      {/* Main Content Area */}
      {view === 'login' && (
        <LoginView onAuthenticate={handleAuthenticate} theme={settings.theme} />
      )}
      {view === 'upload' && (
        <FileUploadView
          onUploadComplete={handleUploadComplete}
          location={location}
          setLocation={setLocation}
          privacyRedaction={settings.privacyRedaction}
          burnAfterReading={settings.burnAfterReading}
        />
      )}
      {view === 'analyzing' && (
        <LiveAnalysisStage
          contractId={contractId}
          fileName={uploadedFile?.name ?? null}
          onComplete={handleAnalysisComplete}
          onRetry={handleReturnToUpload}
          theme={settings.theme}
        />
      )}
      {view === 'workspace' && (
        <WorkspaceResultView
          contractId={contractId}
          onLogout={handleLogout}
          location={location}
          onNewChat={handleReturnToUpload}
          settings={settings}
          setSettings={setSettings}
          uploadedFileName={uploadedFile?.name ?? null}
          analysisReport={analysisReport}
        />
      )}

      {/* Global Footer (Only show outside of workspace) */}
      {view !== 'workspace' && (
        <footer className="mt-auto text-sm font-bold border-t-4 border-ink pt-6 pb-6 flex flex-col sm:flex-row justify-between shrink-0 gap-4 text-ink/60 text-center sm:text-left mx-4 sm:mx-8">
          <span className="flex items-center justify-center sm:justify-start gap-2">
            🐾 动物法律实验室 
            <span className="hidden sm:inline text-ink/30">|</span> 
            <span className="hidden sm:inline">致力于让每一次租房都公平透明</span>
          </span>
          <span className="flex items-center justify-center gap-2">
            <Lock size={14} /> 你的合同数据已被端到端加密保护，房东无法查看。
          </span>
        </footer>
      )}

      {/* Global System Settings Modal */}
      <AnimatePresence>
        {shouldRenderGlobalModal(view, showSystemSettingsModal) && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm p-4 overflow-y-auto"
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-surface border-4 border-ink rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-[8px_8px_0px_var(--color-ink)] my-8"
            >
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-black text-ink flex items-center gap-2">
                  <Settings size={24} className="text-primary" /> 系统设置
                </h3>
                <button onClick={() => setShowSystemSettingsModal(false)} className="text-gray-custom hover:text-ink font-black text-xl">&times;</button>
              </div>

              <div className="space-y-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-black text-ink">隐私消除</div>
                    <div className="text-xs font-bold text-gray-custom mt-1">
                      上传后的合同会先自动脱敏，再进入分析流程。
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={settings.privacyRedaction}
                      onChange={(e) => setSettings({ ...settings, privacyRedaction: e.target.checked })}
                    />
                    <div className="w-11 h-6 bg-ink/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-surface after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-ink/20 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border-2 border-ink"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-black text-ink">桌面通知</div>
                    <div className="text-xs font-bold text-gray-custom mt-1">
                      分析完成后第一时间提醒你。
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={settings.notifications}
                      onChange={(e) => setSettings({ ...settings, notifications: e.target.checked })}
                    />
                    <div className="w-11 h-6 bg-ink/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-surface after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-ink/20 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border-2 border-ink"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-black text-ink">阅后即焚</div>
                    <div className="text-xs font-bold text-gray-custom mt-1">
                      退出登录后自动清除当前合同记录。
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={settings.burnAfterReading}
                      onChange={(e) => setSettings({ ...settings, burnAfterReading: e.target.checked })}
                    />
                    <div className="w-11 h-6 bg-ink/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-surface after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-ink/20 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border-2 border-ink"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-black text-ink">界面主题</div>
                    <div className="text-xs font-bold text-gray-custom mt-1">
                      选择你喜欢的界面风格。
                    </div>
                  </div>
                  <select
                    value={settings.theme}
                    onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
                    className="border-4 border-ink rounded-xl p-3 font-bold bg-paper focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all"
                  >
                    <option value="light">浅色模式</option>
                    <option value="dark">深色模式</option>
                  </select>
                </div>

                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-black text-ink">字体大小</div>
                    <div className="text-xs font-bold text-gray-custom mt-1">
                      调整合同阅读区文字大小。
                    </div>
                  </div>
                  <select
                    value={settings.fontSize}
                    onChange={(e) => setSettings({ ...settings, fontSize: e.target.value })}
                    className="border-4 border-ink rounded-xl p-3 font-bold bg-paper focus:outline-none focus:ring-4 focus:ring-secondary/50 transition-all"
                  >
                    <option value="standard">标准</option>
                    <option value="large">偏大</option>
                    <option value="xlarge">特大</option>
                  </select>
                </div>

                <div className="flex gap-4 mt-6">
                  <button
                    onClick={() => setShowSystemSettingsModal(false)}
                    className="flex-1 py-3 rounded-xl border-4 border-ink font-black text-ink hover:bg-surface-alt transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={() => {
                      setShowSystemSettingsModal(false);
                      alert('系统设置已保存。');
                    }}
                    className="flex-1 py-3 rounded-xl border-4 border-ink bg-primary font-black text-ink shadow-[4px_4px_0px_var(--color-ink)] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all flex items-center justify-center gap-2"
                  >
                    <CheckCircle2 size={18} strokeWidth={3} /> 保存设置
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Global Preferences Modal */}
      <AnimatePresence>
        {shouldRenderGlobalModal(view, showPreferencesModal) && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm p-4 overflow-y-auto"
          >
            <motion.div 
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-surface border-4 border-ink rounded-3xl p-6 sm:p-8 max-w-3xl w-full shadow-[8px_8px_0px_var(--color-ink)] my-8"
            >
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-black text-ink flex items-center gap-2">
                  <User size={24} className="text-primary" /> 🐾 个人偏好
                </h3>
                <button onClick={() => setShowPreferencesModal(false)} className="text-gray-custom hover:text-ink font-black text-xl">&times;</button>
              </div>
              {authUser ? (
                <UserPreferencesSettings
                  userId={authUser.id}
                  onSave={() => {
                    setShowPreferencesModal(false);
                    alert('偏好设置已保存。');
                  }}
                  onClose={() => setShowPreferencesModal(false)}
                />
              ) : (
                <div className="rounded-2xl border-4 border-ink bg-paper p-6 text-center">
                  <p className="text-sm font-black text-ink mb-2">请先登录后再设置个人偏好。</p>
                  <p className="text-xs font-bold text-gray-custom">
                    登录成功后，偏好会直接写入 Supabase 的 user_preferences 表。
                  </p>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
