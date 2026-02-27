"use client";

import { useState } from "react";

interface VerificationResult {
  email: string;
  status: "valid" | "invalid" | "unknown";
  reason: string;
  mx_record: string | null;
  smtp_server: string | null;
  contact_id: number | null;
}

interface FinderResult {
  email: string;
  patterns_tested: number;
  reason: string;
  mx_record: string | null;
  smtp_server: string | null;
  contact_id: number | null;
}

interface HealthCheckResult {
  api: string;
  redis: string;
  database: string;
}

type TabType = "verify" | "find";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>("verify");
  
  // Verify Email Tab
  const [email, setEmail] = useState("");
  const [verifyResult, setVerifyResult] = useState<VerificationResult | null>(null);
  
  // Find Email Tab
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [domain, setDomain] = useState("");
  const [findResult, setFindResult] = useState<FinderResult | null>(null);
  
  // Common
  const [healthResult, setHealthResult] = useState<HealthCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerifyEmail = async () => {
    if (!email) return;
    
    setLoading(true);
    setError(null);
    setVerifyResult(null);
    
    try {
      const response = await fetch("http://localhost:8000/verify-email", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email,
          first_name: "",
          last_name: "",
          domain_id: null,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Erreur HTTP ${response.status}`);
      }
      
      const data: VerificationResult = await response.json();
      setVerifyResult(data);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erreur de connexion au backend");
    } finally {
      setLoading(false);
    }
  };

  const handleFindEmail = async () => {
    if (!firstName || !lastName || !domain) return;
    
    setLoading(true);
    setError(null);
    setFindResult(null);
    
    try {
      const response = await fetch("http://localhost:8000/find-email", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
          domain: domain,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Erreur HTTP ${response.status}`);
      }
      
      const data: FinderResult = await response.json();
      setFindResult(data);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erreur de connexion au backend");
    } finally {
      setLoading(false);
    }
  };

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch("http://localhost:8000/health");
      if (!response.ok) {
        throw new Error(`Erreur HTTP ${response.status}`);
      }
      const data: HealthCheckResult = await response.json();
      setHealthResult(data);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erreur de connexion au backend");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: "valid" | "invalid" | "unknown") => {
    switch (status) {
      case "valid":
        return {
          bgColor: "bg-green-100",
          textColor: "text-green-800",
          borderColor: "border-green-300",
          label: "✓ VALIDE",
        };
      case "invalid":
        return {
          bgColor: "bg-red-100",
          textColor: "text-red-800",
          borderColor: "border-red-300",
          label: "✗ INVALIDE",
        };
      case "unknown":
        return {
          bgColor: "bg-yellow-100",
          textColor: "text-yellow-800",
          borderColor: "border-yellow-300",
          label: "? INCONNU",
        };
    }
  };

  const getHealthStatusColor = (status: string) => {
    if (status === "healthy") return "text-green-600";
    if (status.startsWith("unhealthy")) return "text-red-600";
    return "text-yellow-600";
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="z-10 max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-3">MailKern</h1>
          <p className="text-gray-400">Vérification et recherche d'emails</p>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setActiveTab("verify")}
            className={`flex-1 px-4 py-2 rounded font-semibold transition-colors ${
              activeTab === "verify"
                ? "bg-blue-600 text-white"
                : "text-gray-300 hover:text-white"
            }`}
          >
            Vérifier
          </button>
          <button
            onClick={() => setActiveTab("find")}
            className={`flex-1 px-4 py-2 rounded font-semibold transition-colors ${
              activeTab === "find"
                ? "bg-blue-600 text-white"
                : "text-gray-300 hover:text-white"
            }`}
          >
            Trouver
          </button>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-lg shadow-xl p-8 mb-6">
          {/* VERIFY TAB */}
          {activeTab === "verify" && (
            <>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Adresse email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleVerifyEmail()}
                  placeholder="exemple@domaine.com"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                />
              </div>

              <button
                onClick={handleVerifyEmail}
                disabled={loading || !email}
                className="w-full px-4 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <span className="inline-block animate-spin">⟳</span>
                    Vérification en cours...
                  </>
                ) : (
                  "Valider"
                )}
              </button>

              {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-800 text-sm font-medium">Erreur: {error}</p>
                </div>
              )}

              {verifyResult && !loading && (
                <div className="mt-6 space-y-4">
                  {(() => {
                    const badge = getStatusBadge(verifyResult.status);
                    return (
                      <div className={`p-4 border-2 rounded-lg ${badge.bgColor} ${badge.borderColor}`}>
                        <div className={`text-xl font-bold ${badge.textColor} text-center`}>
                          {badge.label}
                        </div>
                      </div>
                    );
                  })()}

                  <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Email</p>
                      <p className="text-gray-900 break-all">{verifyResult.email}</p>
                    </div>

                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Raison</p>
                      <p className="text-gray-700 text-sm">{verifyResult.reason}</p>
                    </div>

                    {verifyResult.mx_record && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 uppercase">Serveur MX</p>
                        <p className="text-gray-900 font-mono text-sm">{verifyResult.mx_record}</p>
                      </div>
                    )}

                    {verifyResult.smtp_server && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 uppercase">Serveur SMTP</p>
                        <p className="text-gray-900 font-mono text-sm">{verifyResult.smtp_server}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          {/* FIND TAB */}
          {activeTab === "find" && (
            <>
              <div className="space-y-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Prénom
                  </label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="John"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nom
                  </label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="Doe"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Domaine
                  </label>
                  <input
                    type="text"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleFindEmail()}
                    placeholder="example.com"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                  />
                </div>
              </div>

              <button
                onClick={handleFindEmail}
                disabled={loading || !firstName || !lastName || !domain}
                className="w-full px-4 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <span className="inline-block animate-spin">⟳</span>
                    Recherche en cours...
                  </>
                ) : (
                  "Trouver l'email"
                )}
              </button>

              {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-800 text-sm font-medium">Erreur: {error}</p>
                </div>
              )}

              {findResult && !loading && (
                <div className="mt-6 space-y-4">
                  <div className="p-4 border-2 border-green-300 bg-green-100 rounded-lg">
                    <div className="text-xl font-bold text-green-800 text-center break-all">
                      {findResult.email}
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Patterns testés</p>
                      <p className="text-gray-900 font-mono text-sm">{findResult.patterns_tested}</p>
                    </div>

                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase">Raison</p>
                      <p className="text-gray-700 text-sm">{findResult.reason}</p>
                    </div>

                    {findResult.mx_record && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 uppercase">Serveur MX</p>
                        <p className="text-gray-900 font-mono text-sm">{findResult.mx_record}</p>
                      </div>
                    )}

                    {findResult.smtp_server && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 uppercase">Serveur SMTP</p>
                        <p className="text-gray-900 font-mono text-sm">{findResult.smtp_server}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Health Check Button */}
        <div className="text-center">
          <button
            onClick={checkHealth}
            disabled={loading}
            className="text-sm text-gray-400 hover:text-gray-300 underline disabled:opacity-50"
          >
            {loading ? "Vérification..." : "Vérifier l'état des services"}
          </button>
        </div>

        {/* Health Check Result */}
        {healthResult && (
          <div className="mt-4 bg-gray-800 rounded-lg p-4">
            <h3 className="text-white font-semibold mb-3 text-sm">État des services</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-300">API:</span>
                <span className={getHealthStatusColor(healthResult.api)}>
                  {healthResult.api}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Redis:</span>
                <span className={getHealthStatusColor(healthResult.redis)}>
                  {healthResult.redis}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Database:</span>
                <span className={getHealthStatusColor(healthResult.database)}>
                  {healthResult.database}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
