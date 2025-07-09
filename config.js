require('dotenv').config();

const stripeSecretKey = process.env.STRIPE_SECRET_KEY;

if (!stripeSecretKey) {
  throw new Error('STRIPE_SECRET_KEY is not set in the environment');
}

module.exports = {
  port: process.env.PORT || 4242,
  stripeSecretKey,
};
