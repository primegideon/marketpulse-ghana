// ui/api/prices.js
// Vercel Edge Function — MarketPulse Ghana Public Price API
//
// Exposes a lightweight JSON endpoint for programmatic access to
// Ghana food price intelligence. Suitable for NGOs, researchers, and
// government systems that want machine-readable current price data.
//
// Endpoint: GET /api/prices?commodity=Maize&type=Wholesale
//
// Because Evidence.dev builds a fully static site, this edge function
// returns structured metadata and documentation. For full historical
// data access, consumers should use the DuckDB mart schema directly
// (see: https://github.com/primegideon/marketpulse-ghana).

export const config = {
  runtime: 'edge',
};

const COMMODITIES = [
  'Cassava', 'Cowpeas', 'Groundnuts (shelled)', 'Maize', 'Millet',
  'Onions', 'Plantains', 'Rice (imported)', 'Rice (local)', 'Sorghum',
  'Tomatoes (local)', 'Yam',
];

const PRICE_TYPES = ['Wholesale', 'Retail'];

const REGIONS = [
  'Ashanti', 'Brong-Ahafo', 'Central', 'Eastern',
  'Greater Accra', 'Northern', 'Upper East', 'Upper West', 'Volta', 'Western',
];

export default async function handler(request) {
  const url = new URL(request.url);
  const commodity = url.searchParams.get('commodity');
  const priceType = url.searchParams.get('type') || 'Wholesale';

  // Validate inputs
  const errors = [];
  if (commodity && !COMMODITIES.includes(commodity)) {
    errors.push(`Unknown commodity '${commodity}'. Valid options: ${COMMODITIES.join(', ')}`);
  }
  if (!PRICE_TYPES.includes(priceType)) {
    errors.push(`Unknown price type '${priceType}'. Valid options: ${PRICE_TYPES.join(', ')}`);
  }

  if (errors.length > 0) {
    return new Response(
      JSON.stringify({ error: 'Invalid request parameters', details: errors }, null, 2),
      {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }
    );
  }

  const response = {
    api: 'MarketPulse Ghana Price Intelligence API',
    version: '1.0.0',
    description: [
      'Ghana agricultural commodity price intelligence derived from the',
      'UN World Food Programme (WFP) Humanitarian Data Exchange (HDX) dataset.',
      'Covers 26 food staples across 44 markets and 10 administrative regions',
      'from 2006 to present, updated monthly.',
    ].join(' '),

    request: {
      commodity: commodity || 'all',
      price_type: priceType,
      timestamp: new Date().toISOString(),
    },

    // Guidance for data consumers
    data_access: {
      dashboard: 'https://marketpulse-ghana.vercel.app',
      repository: 'https://github.com/primegideon/marketpulse-ghana',
      database_schema: 'DuckDB mart tables — see /ui/sources/agri_ghana/*.sql',
      full_dataset_url: 'https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320',
      note: [
        'This edge function provides API metadata and routing.',
        'For programmatic bulk access to the full time-series data,',
        'clone the repository and open agri_ghana.duckdb directly,',
        'or query the mart views via the Evidence.dev source layer.',
      ].join(' '),
    },

    catalog: {
      commodities: COMMODITIES,
      price_types: PRICE_TYPES,
      regions: REGIONS,
      markets_count: 44,
      date_range: { from: '2006-01-01', to: 'present (monthly updates)' },
    },

    marts: {
      mart_commodity_monthly: 'National monthly median prices with MoM/YoY change and price_signal',
      mart_regional_spreads: 'Per-market price spreads vs national median with lat/long',
      mart_wholesale_retail_margins: 'Wholesale-to-retail markup by market and commodity',
      mart_commodity_monthly_real: 'CPI-deflated real prices (base year 2015)',
      mart_maize_forecasts: '3-month XGBoost price forecasts with 95% confidence intervals',
      mart_market_connectivity: 'Spatial price integration score per commodity',
      dim_exchange_rates: 'Implied GHS/USD exchange rate derived from WFP survey data',
    },

    contact: {
      maintainer: 'Gideon Owusu Amoah',
      email: 'deon.owusu006@gmail.com',
      co_maintainer: 'Emmanuel Twumasi-Kwame Yeboah',
    },

    status: 'available',
  };

  return new Response(JSON.stringify(response, null, 2), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400',
    },
  });
}

