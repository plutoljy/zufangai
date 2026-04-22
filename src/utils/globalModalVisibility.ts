export type AppView = 'login' | 'upload' | 'analyzing' | 'workspace';

export function shouldRenderGlobalModal(view: AppView, isOpen: boolean) {
  return isOpen && view !== 'login';
}
