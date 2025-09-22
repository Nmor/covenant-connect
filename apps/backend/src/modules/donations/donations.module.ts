import { Module } from '@nestjs/common';

import { DonationsController } from './donations.controller';
import { DonationsService } from './donations.service';
import { PaystackPaymentProvider } from './providers/paystack.provider';
import { FincraPaymentProvider } from './providers/fincra.provider';
import { StripePaymentProvider } from './providers/stripe.provider';
import { FlutterwavePaymentProvider } from './providers/flutterwave.provider';

@Module({
  controllers: [DonationsController],
  providers: [
    DonationsService,
    PaystackPaymentProvider,
    FincraPaymentProvider,
    StripePaymentProvider,
    FlutterwavePaymentProvider
  ],
  exports: [DonationsService]
})
export class DonationsModule {}
