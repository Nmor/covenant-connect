declare module '@aws-sdk/client-ses' {
  export interface SendEmailCommandInput {
    Message?: {
      Body?: {
        Html?: { Data?: string };
        Text?: { Data?: string };
      };
      Subject?: { Data?: string };
    };
    ConfigurationSetName?: string;
    ReplyToAddresses?: string[];
    Destination?: Record<string, unknown>;
    Source?: string;
  }

  export class SESClient {
    constructor(config?: Record<string, unknown>);
    send(command: SendEmailCommand): Promise<void>;
  }

  export class SendEmailCommand {
    constructor(input: SendEmailCommandInput);
    readonly input: SendEmailCommandInput;
  }
}
