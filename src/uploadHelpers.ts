export type UploadFormat = 'pdf' | 'word' | 'image';
export type UploadTargetFormat = UploadFormat | 'all';

export interface FileLike {
  name: string;
  size: number;
  type?: string;
}

export interface UploadValidationResult {
  ok: boolean;
  error?: string;
  file?: FileLike;
}

export const MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024;

const ACCEPTED_FORMATS: Record<
  UploadFormat,
  {
    accept: string[];
    extensions: string[];
    mimeTypes: string[];
    label: string;
  }
> = {
  pdf: {
    accept: ['.pdf', 'application/pdf'],
    extensions: ['pdf'],
    mimeTypes: ['application/pdf'],
    label: 'PDF',
  },
  word: {
    accept: [
      '.doc',
      '.docx',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ],
    extensions: ['doc', 'docx'],
    mimeTypes: [
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ],
    label: 'Word',
  },
  image: {
    accept: ['.png', '.jpg', '.jpeg', 'image/png', 'image/jpeg'],
    extensions: ['png', 'jpg', 'jpeg'],
    mimeTypes: ['image/png', 'image/jpeg'],
    label: 'PNG/JPG',
  },
};

const ALL_ACCEPT_VALUES = Array.from(
  new Set(
    Object.values(ACCEPTED_FORMATS).flatMap((format) => format.accept)
  )
);

export function getUploadAccept(format: UploadTargetFormat = 'all'): string {
  if (format === 'all') {
    return ALL_ACCEPT_VALUES.join(',');
  }

  return ACCEPTED_FORMATS[format].accept.join(',');
}

export function getUploadHint(format: UploadTargetFormat = 'all'): string {
  if (format === 'all') {
    return '支持 PDF、Word、PNG/JPG 文件，最大 50MB';
  }

  return `支持 ${ACCEPTED_FORMATS[format].label} 文件，最大 50MB`;
}

export function openNativeFileDialog(
  input: Pick<HTMLInputElement, 'click'> | null | undefined
): boolean {
  if (!input) {
    return false;
  }

  input.click();
  return true;
}

export function validateUploadSelection(
  files: readonly FileLike[] | null | undefined,
  format: UploadTargetFormat = 'all'
): UploadValidationResult {
  if (!files || files.length === 0) {
    return { ok: false, error: '请选择一个要上传的文件。' };
  }

  if (files.length > 1) {
    return { ok: false, error: '一次只能上传 1 个文件。' };
  }

  const [file] = files;
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return { ok: false, error: '文件大小不能超过 50MB。' };
  }

  if (!matchesAcceptedFormat(file, format)) {
    return {
      ok: false,
      error:
        format === 'all'
          ? '当前仅支持 PDF、Word、PNG/JPG 文件。'
          : `当前仅支持 ${ACCEPTED_FORMATS[format].label} 格式文件。`,
    };
  }

  return { ok: true, file };
}

export function detectUploadFormat(file: FileLike): UploadFormat | null {
  const matchedFormat = (Object.keys(ACCEPTED_FORMATS) as UploadFormat[]).find(
    (format) => matchesSingleFormat(file, format)
  );

  return matchedFormat ?? null;
}

function matchesAcceptedFormat(file: FileLike, format: UploadTargetFormat): boolean {
  if (format === 'all') {
    return detectUploadFormat(file) !== null;
  }

  return matchesSingleFormat(file, format);
}

function matchesSingleFormat(file: FileLike, format: UploadFormat): boolean {
  const rule = ACCEPTED_FORMATS[format];
  const mimeType = (file.type ?? '').toLowerCase();

  if (mimeType && rule.mimeTypes.includes(mimeType)) {
    return true;
  }

  const extension = getExtension(file.name);
  return Boolean(extension) && rule.extensions.includes(extension);
}

function getExtension(fileName: string): string {
  const parts = fileName.toLowerCase().split('.');
  return parts.length > 1 ? parts.at(-1) ?? '' : '';
}
