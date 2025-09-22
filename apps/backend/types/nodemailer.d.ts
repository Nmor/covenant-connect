declare module 'nodemailer' {
  export type TransportOptions = Record<string, unknown>;

  export type Transporter = {
    sendMail(message: Record<string, unknown>): Promise<void>;
  };

  export function createTransport(options: TransportOptions): Transporter;

  const nodemailer: {
    createTransport: typeof createTransport;
  };

  export default nodemailer;
}
