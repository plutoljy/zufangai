export function normalizeApiError(error: unknown): Error {
  if (error instanceof TypeError && error.message === 'Failed to fetch') {
    return new Error(
      '无法连接上传接口，请确认后端已启动，并允许当前前端地址访问。'
    );
  }

  if (error instanceof Error) {
    return error;
  }

  return new Error('请求过程中发生未知错误。');
}
