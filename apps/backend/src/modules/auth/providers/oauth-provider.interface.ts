import type { Provider } from '@covenant-connect/shared';

export type OAuthProvider = Exclude<Provider, 'password'>;

export type OAuthTokens = {
  accessToken: string;
  refreshToken?: string;
  expiresAt?: Date;
};

export type OAuthProfile = {
  provider: OAuthProvider;
  providerId: string;
  email: string;
  firstName: string;
  lastName: string;
  avatarUrl?: string;
};

export type OAuthExchangeResult = OAuthProfile & {
  tokens: OAuthTokens;
};

export type AuthorizationUrlParams = {
  state: string;
  redirectUri?: string;
};

export type CodeExchangeParams = {
  code: string;
  redirectUri?: string;
};

export interface OAuthProviderStrategy {
  readonly provider: OAuthProvider;
  createAuthorizationUrl(params: AuthorizationUrlParams): string;
  exchangeCode(params: CodeExchangeParams): Promise<OAuthExchangeResult>;
}
