export type EmailProviderErrorCode = 'configuration' | 'transport' | 'unknown';

export class EmailProviderError extends Error {
  constructor(
    public readonly code: EmailProviderErrorCode,
    message: string,
    options?: { cause?: unknown }
  ) {
    super(message);
    if (options?.cause !== undefined) {
      (this as { cause?: unknown }).cause = options.cause;
    }
    this.name = 'EmailProviderError';
  }

  static configuration(message: string, cause?: unknown): EmailProviderError {
    return new EmailProviderError('configuration', message, cause ? { cause } : undefined);
  }

  static transport(message: string, cause?: unknown): EmailProviderError {
    return new EmailProviderError('transport', message, cause ? { cause } : undefined);
  }

  static unknown(message: string, cause?: unknown): EmailProviderError {
    return new EmailProviderError('unknown', message, cause ? { cause } : undefined);
  }
}
