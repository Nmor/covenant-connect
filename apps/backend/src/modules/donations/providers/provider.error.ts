export type DonationProviderErrorType = 'validation' | 'processing';

export class DonationProviderError extends Error {
  constructor(readonly message: string, readonly type: DonationProviderErrorType) {
    super(message);
    this.name = 'DonationProviderError';
  }

  static validation(message: string): DonationProviderError {
    return new DonationProviderError(message, 'validation');
  }

  static processing(message: string): DonationProviderError {
    return new DonationProviderError(message, 'processing');
  }
}
