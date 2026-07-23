"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type StockData = {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercentage: number;
  marketCap: number;
  dayLow: number;
  dayHigh: number;
  yearLow: number;
  yearHigh: number;
  volume: number;
  exchange: string;
};

type HistoryPoint = {
  date: string;
  close: number;
  high: number;
  low: number;
  volume: number;
};

type CompanyProfile = {
  symbol: string;
  companyName: string;
  sector: string | null;
  industry: string | null;
  ceo: string | null;
  website: string | null;
  description: string | null;
  country: string | null;
  employees: string | null;
  ipoDate: string | null;
  image: string | null;
  exchange: string | null;
};

type Fundamentals = {
  symbol: string;
  fiscalDate: string | null;
  peRatio: number | null;
  eps: number | null;
  dividendPerShare: number | null;
  revenue: number | null;
  revenueGrowth: number | null;
  netIncome: number | null;
  netMargin: number | null;
  grossProfit: number | null;
  operatingIncome: number | null;
  ebitda: number | null;
};

type FinancialHealth = {
  symbol: string;
  fiscalDate: string | null;
  cashAndCashEquivalents: number | null;
  totalDebt: number | null;
  totalAssets: number | null;
  totalLiabilities: number | null;
  shareholdersEquity: number | null;
  currentRatio: number | null;
  debtToEquity: number | null;
  operatingCashFlow: number | null;
  capitalExpenditures: number | null;
  freeCashFlow: number | null;
};

type HistoryPeriod = "1M" | "6M" | "1Y" | "5Y";

const HISTORY_PERIODS: HistoryPeriod[] = ["1M", "6M", "1Y", "5Y"];

function formatPrice(value: number) {
  return `$${value.toFixed(2)}`;
}

function formatMarketCap(value: number) {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  return `$${value.toLocaleString()}`;
}

export default function StockPage() {
  const params = useParams<{ ticker: string }>();
  const ticker = params.ticker.toUpperCase();

  const [stock, setStock] = useState<StockData | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [fundamentals, setFundamentals] = useState<Fundamentals | null>(null);
  const [financialHealth, setFinancialHealth] =
    useState<FinancialHealth | null>(null);
  const [period, setPeriod] = useState<HistoryPeriod>("1Y");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    const loadStockDetails = async () => {
      setLoading(true);
      setError("");
      setProfile(null);
      setFundamentals(null);
      setFinancialHealth(null);

      try {
        const quoteResponse = await fetch(
          `http://localhost:8000/stock/${ticker}`
        );
        const quoteData = await quoteResponse.json();

        if (!quoteResponse.ok) {
          throw new Error(quoteData.error || "Stock data could not be found.");
        }

        if (!Array.isArray(quoteData) || quoteData.length === 0) {
          throw new Error("Stock data cound not be found.");
        }

        setStock(quoteData[0]);

        const [
          profileResponse,
          fundamentalsResponse,
          financialHealthResponse,
        ] = await Promise.all([
          fetch(`http://localhost:8000/stock/${ticker}/profile`),
          fetch(`http://localhost:8000/stock/${ticker}/fundamentals`),
          fetch(`http://localhost:8000/stock/${ticker}/financial-health`),
        ]);

        if (profileResponse.ok) {
          const profileData: CompanyProfile = await profileResponse.json();
          setProfile(profileData);
        }

        if (fundamentalsResponse.ok) {
          const fundamentalsData: Fundamentals =
            await fundamentalsResponse.json();
          setFundamentals(fundamentalsData);
        }

        if (financialHealthResponse.ok) {
          const healthData: FinancialHealth =
            await financialHealthResponse.json();
          setFinancialHealth(healthData);
        }
      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Unable to load stock data."
        );
      } finally {
        setLoading(false);
      }
    };

    loadStockDetails();
  }, [ticker]);

  useEffect(() => {
    const loadHistory = async () => {
      setHistoryLoading(true);

      try {
        const historyResponse = await fetch(
          `http://localhost:8000/stock/${ticker}/history?period=${period}`
        );
        const historyData = await historyResponse.json();

        if (!historyResponse.ok) {
          throw new Error(
            historyData.detail || "Historical data could not be loaded."
          );
        }

        if (!Array.isArray(historyData.history)) {
          throw new Error("Historical data could not be loaded.");
        }

        setHistory(historyData.history);
      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Historical data could not be loaded."
        );
      } finally {
        setHistoryLoading(false);
      }
    };

    loadHistory();
  }, [ticker, period]);

  const isPositive = stock ? stock.change >= 0 : true;

  const performance =
    history.length > 0
      ? {
          high: Math.max(...history.map((point) => point.high)),
          low: Math.min(...history.map((point) => point.low)),
          returnPercent:
            ((history[history.length - 1].close - history[0].close) /
              history[0].close) *
            100,
        }
      : null;

  return (
    <main
      className="min-h-screen"
      style={{
        backgroundColor: "#0B1120",
        color: "#EDEBE3",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <nav
        className="flex items-center gap-6 px-6 py-4"
        style={{
          borderBottom: "1px solid #1E2A3D",
          backgroundColor: "#0E1726",
        }}
      >
        <Link
          href="/dashboard"
          className="text-sm font-semibold"
          style={{
            color: "#EDEBE3",
            fontFamily: "'IBM Plex Mono', monospace",
          }}
        >
          STRATOS
        </Link>

        <Link
          href="/dashboard"
          className="text-sm"
          style={{ color: "#8A93A6" }}
        >
          Research Dashboard
        </Link>
      </nav>

      <section className="w-full max-w-[1600px] mx-auto px-8 py-14">
        {loading && (
          <p style={{ color: "#8A93A6" }}>
            Loading {ticker} data...
          </p>
        )}

        {error && <p style={{ color: "#B5675A" }}>{error}</p>}

        {stock && (
          <>
            <p
              className="text-xs uppercase mb-2"
              style={{
                letterSpacing: "0.15em",
                color: "#8A93A6",
                fontFamily: "'IBM Plex Mono', monospace",
              }}
            >
              Company Research
            </p>

            <div className="flex flex-wrap items-end justify-between gap-5 pb-8">
              <div>
                <h1 className="text-4xl font-semibold">{stock.symbol}</h1>
                <p className="mt-2 text-base" style={{ color: "#8A93A6" }}>
                  {stock.name}
                </p>
              </div>

              <div className="text-right">
                <p
                  className="text-3xl"
                  style={{ fontFamily: "'IBM Plex Mono', monospace" }}
                >
                  {formatPrice(stock.price)}
                </p>
                <p
                  className="mt-1 text-sm"
                  style={{
                    color: isPositive ? "#7FA37A" : "#B5675A",
                    fontFamily: "'IBM Plex Mono', monospace",
                  }}
                >
                  {isPositive ? "+" : ""}
                  {stock.change.toFixed(2)} ({isPositive ? "+" : ""}
                  {stock.changePercentage.toFixed(2)}%)
                </p>
              </div>
            </div>

            <div className="grid gap-8 lg:grid-cols-[220px_minmax(0,1fr)_280px]">
              {financialHealth && (
                <aside
                  className="h-fit p-5"
                  style={{
                    backgroundColor: "#0E1726",
                    border: "1px solid #1E2A3D",
                  }}
                >
                  <p
                    className="text-xs uppercase"
                    style={{
                      letterSpacing: "0.15em",
                      color: "#8A93A6",
                      fontFamily: "'IBM Plex Mono', monospace",
                    }}
                  >
                    Financial Health
                  </p>

                  <h2 className="mt-2 text-lg font-semibold">
                    Balance Sheet & Cash Flow
                  </h2>

                  <div className="mt-5">
                    {[
                      [
                        "Cash",
                        financialHealth.cashAndCashEquivalents !== null
                          ? formatMarketCap(
                              financialHealth.cashAndCashEquivalents
                            )
                          : "—",
                      ],
                      [
                        "Total Debt",
                        financialHealth.totalDebt !== null
                          ? formatMarketCap(financialHealth.totalDebt)
                          : "—",
                      ],
                      [
                        "Current Ratio",
                        financialHealth.currentRatio !== null
                          ? financialHealth.currentRatio.toFixed(2)
                          : "—",
                      ],
                      [
                        "Debt / Equity",
                        financialHealth.debtToEquity !== null
                          ? financialHealth.debtToEquity.toFixed(2)
                          : "—",
                      ],
                      [
                        "Operating Cash Flow",
                        financialHealth.operatingCashFlow !== null
                          ? formatMarketCap(financialHealth.operatingCashFlow)
                          : "—",
                      ],
                      [
                        "Free Cash Flow",
                        financialHealth.freeCashFlow !== null
                          ? formatMarketCap(financialHealth.freeCashFlow)
                          : "—",
                      ],
                    ].map(([label, value], index) => (
                      <div
                        key={label}
                        className="py-3"
                        style={{
                          borderBottom:
                            index < 5 ? "1px solid #1E2A3D" : "none",
                        }}
                      >
                        <p className="text-xs" style={{ color: "#8A93A6" }}>
                          {label}
                        </p>
                        <p
                          className="mt-1 text-sm"
                          style={{
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>
                </aside>
              )}

              <div>
                <div
                  className="grid grid-cols-2 md:grid-cols-4"
                  style={{
                    borderTop: "1px solid #1E2A3D",
                    borderLeft: "1px solid #1E2A3D",
                  }}
                >
                  {[
                    ["Market Cap", formatMarketCap(stock.marketCap)],
                    ["Volume", stock.volume.toLocaleString()],
                    [
                      "Day Range",
                      `${formatPrice(stock.dayLow)} - ${formatPrice(
                        stock.dayHigh
                      )}`,
                    ],
                    [
                      "52 Week Range",
                      `${formatPrice(stock.yearLow)} - ${formatPrice(
                        stock.yearHigh
                      )}`,
                    ],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      className="p-5"
                      style={{
                        borderRight: "1px solid #1E2A3D",
                        borderBottom: "1px solid #1E2A3D",
                      }}
                    >
                      <p
                        className="text-xs mb-2"
                        style={{ color: "#8A93A6" }}
                      >
                        {label}
                      </p>
                      <p
                        className="text-sm"
                        style={{
                          fontFamily: "'IBM Plex Mono', monospace",
                        }}
                      >
                        {value}
                      </p>
                    </div>
                  ))}
                </div>

                {historyLoading ? (
                  <p
                    className = "mt-10 pt-6 text-sm"
                    style = {{ 
                      color: "#8A93A6",
                      borderTop: "1px solid #1E2A3D",
                    }}
                  >
                    Loading performance data...
                  </p>
                ) : performance && (
                  <section
                    className="mt-10 pt-6"
                    style={{ borderTop: "1px solid #1E2A3D" }}
                  >
                    <div className="flex items-center justify-between mb-5">
                      <h2 className="text-lg font-semibold">
                        {period} Performance
                      </h2>

                      <div className="flex gap-1">
                        {HISTORY_PERIODS.map((option) => (
                          <button
                            key={option}
                            onClick={() => setPeriod(option)}
                            className="px-2.5 py-1 text-xs rounded-sm"
                            style={{
                              backgroundColor:
                                period === option ? "#C9963C" : "#1E2A3D",
                              color:
                                period === option ? "#0B1120" : "#EDEBE3",
                            }}
                          >
                            {option}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p
                          className="text-xs mb-1"
                          style={{ color: "#8A93A6" }}
                        >
                          Return
                        </p>
                        <p
                          className="text-base"
                          style={{
                            color:
                              performance.returnPercent >= 0
                                ? "#7FA37A"
                                : "#B5675A",
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >
                          {performance.returnPercent >= 0 ? "+" : ""}
                          {performance.returnPercent.toFixed(2)}%
                        </p>
                      </div>

                      <div>
                        <p
                          className="text-xs mb-1"
                          style={{ color: "#8A93A6" }}
                        >
                          Period High
                        </p>
                        <p
                          className="text-base"
                          style={{
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >
                          {formatPrice(performance.high)}
                        </p>
                      </div>

                      <div>
                        <p
                          className="text-xs mb-1"
                          style={{ color: "#8A93A6" }}
                        >
                          Period Low
                        </p>
                        <p
                          className="text-base"
                          style={{
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >
                          {formatPrice(performance.low)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-8 h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={history}
                          margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                        >
                          <CartesianGrid
                            stroke="#1E2A3D"
                            strokeDasharray="3 3"
                          />

                          <XAxis
                            dataKey="date"
                            tick={{ fill: "#8A93A6", fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={35}
                            tickFormatter={(value) =>
                              new Date(
                                `${value}T00:00:00`
                              ).toLocaleDateString("en-US", {
                                month: "short",
                                year: "2-digit",
                              })
                            }
                          />

                          <YAxis
                            dataKey="close"
                            tick={{ fill: "#8A93A6", fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            width={52}
                            tickFormatter={(value) => `$${value}`}
                            domain={["dataMin", "dataMax"]}
                          />

                          <Tooltip
                            contentStyle={{
                              backgroundColor: "#0E1726",
                              border: "1px solid #1E2A3D",
                              borderRadius: "2px",
                              color: "#EDEBE3",
                            }}
                            labelStyle={{ color: "#8A93A6" }}
                          />

                          <Line
                            type="monotone"
                            dataKey="close"
                            name="Close"
                            stroke="#C9963C"
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 4, fill: "#C9963C" }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </section>
                )}

                {profile && (
                  <section
                    className="mt-10 pt-6"
                    style={{ borderTop: "1px solid #1E2A3D" }}
                  >
                    <div className="flex items-center gap-4 mb-5">
                      {profile.image && (
                        <img
                          src={profile.image}
                          alt={`${profile.companyName} logo`}
                          className="w-12 h-12 rounded-sm"
                        />
                      )}

                      <div>
                        <p
                          className="text-xs uppercase"
                          style={{
                            letterSpacing: "0.15em",
                            color: "#8A93A6",
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >
                          Company Overview
                        </p>
                        <h2 className="text-xl font-semibold mt-1">
                          {profile.companyName}
                        </h2>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      {[
                        ["Sector", profile.sector || "—"],
                        ["Industry", profile.industry || "—"],
                        ["Exchange", profile.exchange || "—"],
                        ["CEO", profile.ceo || "—"],
                        [
                          "Founded",
                          profile.ipoDate
                            ? profile.ipoDate.slice(0, 4)
                            : "—",
                        ],
                      ].map(([label, value]) => (
                        <div key={label}>
                          <p
                            className="text-xs mb-1"
                            style={{ color: "#8A93A6" }}
                          >
                            {label}
                          </p>
                          <p className="text-sm">{value}</p>
                        </div>
                      ))}
                    </div>

                    {profile.description && (
                      <p
                        className="text-sm leading-6"
                        style={{ color: "#B8BFCC" }}
                      >
                        {profile.description}
                      </p>
                    )}

                    {profile.website && (
                      <a
                        href={profile.website}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-block mt-5 text-sm"
                        style={{ color: "#C9963C" }}
                      >
                        Visit Company Website →
                      </a>
                    )}
                  </section>
                )}
              </div>

              <aside
                className="h-fit p-5"
                style={{
                  backgroundColor: "#0E1726",
                  border: "1px solid #1E2A3D",
                }}
              >
                <p
                  className="text-xs uppercase mb-4"
                  style={{
                    letterSpacing: "0.15em",
                    color: "#8A93A6",
                    fontFamily: "'IBM Plex Mono', monospace",
                  }}
                >
                  Fundamentals
                </p>

                {fundamentals ? (
                  <div>
                    {[
                      [
                        "P/E Ratio",
                        fundamentals.peRatio !== null
                          ? fundamentals.peRatio.toFixed(1)
                          : "—",
                      ],
                      [
                        "EPS",
                        fundamentals.eps !== null
                          ? formatPrice(fundamentals.eps)
                          : "—",
                      ],
                      [
                        "Revenue",
                        fundamentals.revenue !== null
                          ? formatMarketCap(fundamentals.revenue)
                          : "—",
                      ],
                      [
                        "Revenue Growth",
                        fundamentals.revenueGrowth !== null
                          ? `${fundamentals.revenueGrowth.toFixed(1)}%`
                          : "—",
                      ],
                      [
                        "Net Income",
                        fundamentals.netIncome !== null
                          ? formatMarketCap(fundamentals.netIncome)
                          : "—",
                      ],
                      [
                        "Net Margin",
                        fundamentals.netMargin !== null
                          ? `${fundamentals.netMargin.toFixed(1)}%`
                          : "—",
                      ],
                    ].map(([label, value], index) => (
                      <div
                        key={label}
                        className="flex items-center justify-between py-3"
                        style={{
                          borderBottom:
                            index < 5 ? "1px solid #1E2A3D" : "none",
                        }}
                      >
                        <span
                          className="text-sm"
                          style={{ color: "#8A93A6" }}
                        >
                          {label}
                        </span>
                        <span
                          className="text-sm"
                          style={{
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >
                          {value}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm" style={{ color: "#8A93A6" }}>
                    Fundamentals unavailable for this stock.
                  </p>
                )}
              </aside>
            </div>
          </>
        )}
      </section>
    </main>
  );
}