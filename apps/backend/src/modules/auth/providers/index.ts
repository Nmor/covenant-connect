export { AppleOAuthProvider } from './apple.provider';
export { FacebookOAuthProvider } from './facebook.provider';
export { GoogleOAuthProvider } from './google.provider';
export type {
  AuthorizationUrlParams,
  CodeExchangeParams,
  OAuthExchangeResult,
  OAuthProvider,
  OAuthProviderStrategy,
  OAuthTokens
} from './oauth-provider.interface';

export const AUTH_PROVIDER_STRATEGIES = Symbol('AUTH_PROVIDER_STRATEGIES');
