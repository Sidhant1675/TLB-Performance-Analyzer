#include <iostream>
#include <vector>
#include <queue>
#include <list>
#include <unordered_map>
#include <unordered_set>
#include <iomanip>
#include <string>
#include <sstream>
#include <cmath>

using namespace std;

const double TLB_ACCESS_TIME = 1.0;
const double MEMORY_ACCESS_TIME = 10.0;

struct SimResult {
    int totalAccesses;
    int hits;
    int misses;
    double hitRate;
    double missRate;
    double emat;
    string policy;
    int tlbSize;
};

struct StepInfo {
    int address;
    int pageNumber;
    bool hit;
    string tlbState;
};

string formatTlbState(const vector<int>& entries) {
    if (entries.empty()) return "{ empty }";
    stringstream ss;
    ss << "{ ";
    for (int i = 0; i < (int)entries.size(); i++) {
        if (i > 0) ss << ", ";
        ss << entries[i];
    }
    ss << " }";
    return ss.str();
}

vector<int> fifoGetEntries(const queue<int>& q) {
    queue<int> copy = q;
    vector<int> v;
    while (!copy.empty()) {
        v.push_back(copy.front());
        copy.pop();
    }
    return v;
}

vector<int> lruGetEntries(const list<int>& lst) {
    return vector<int>(lst.begin(), lst.end());
}

SimResult runSimulation(const vector<int>& addresses, int pageSize, int tlbSize,
                        const string& policy, bool traceEnabled) {
    int hits = 0, misses = 0;
    vector<StepInfo> trace;

    if (policy == "FIFO") {
        unordered_set<int> tlbSet;
        queue<int> tlbQueue;

        for (int addr : addresses) {
            int page = addr / pageSize;
            bool hit = tlbSet.count(page) > 0;

            if (hit) {
                hits++;
            } else {
                misses++;
                if ((int)tlbSet.size() >= tlbSize) {
                    int victim = tlbQueue.front();
                    tlbQueue.pop();
                    tlbSet.erase(victim);
                }
                tlbSet.insert(page);
                tlbQueue.push(page);
            }

            if (traceEnabled) {
                trace.push_back({addr, page, hit, formatTlbState(fifoGetEntries(tlbQueue))});
            }
        }
    } else {
        list<int> tlbList;
        unordered_map<int, list<int>::iterator> tlbMap;

        for (int addr : addresses) {
            int page = addr / pageSize;
            bool hit = tlbMap.count(page) > 0;

            if (hit) {
                hits++;
                tlbList.erase(tlbMap[page]);
                tlbList.push_back(page);
                tlbMap[page] = prev(tlbList.end());
            } else {
                misses++;
                if ((int)tlbList.size() >= tlbSize) {
                    int victim = tlbList.front();
                    tlbList.pop_front();
                    tlbMap.erase(victim);
                }
                tlbList.push_back(page);
                tlbMap[page] = prev(tlbList.end());
            }

            if (traceEnabled) {
                trace.push_back({addr, page, hit, formatTlbState(lruGetEntries(tlbList))});
            }
        }
    }

    int total = hits + misses;
    double hitRate = total > 0 ? (double)hits / total : 0.0;
    double missRate = total > 0 ? (double)misses / total : 0.0;
    double emat = (hitRate * TLB_ACCESS_TIME) + (missRate * (TLB_ACCESS_TIME + MEMORY_ACCESS_TIME));

    if (traceEnabled) {
        cout << "\n";
        cout << "  Step-by-Step Trace  [" << policy << ", TLB size=" << tlbSize << "]\n";
        cout << "  " << string(76, '-') << "\n";
        cout << "  " << left << setw(6) << "#"
             << setw(10) << "Addr"
             << setw(8) << "Page"
             << setw(10) << "Result"
             << "TLB State\n";
        cout << "  " << string(76, '-') << "\n";

        for (int i = 0; i < (int)trace.size(); i++) {
            cout << "  " << left << setw(6) << (i + 1)
                 << setw(10) << trace[i].address
                 << setw(8) << trace[i].pageNumber
                 << setw(10) << (trace[i].hit ? "HIT" : "MISS")
                 << trace[i].tlbState << "\n";
        }
        cout << "  " << string(76, '-') << "\n";
    }

    return {total, hits, misses, hitRate, missRate, emat, policy, tlbSize};
}

void printResultsTable(const vector<SimResult>& results) {
    cout << "\n  " << string(82, '=') << "\n";
    cout << "  MULTI-SIZE TLB ANALYSIS\n";
    cout << "  " << string(82, '-') << "\n";
    cout << "  " << left
         << setw(10) << "Policy"
         << setw(10) << "TLB Size"
         << setw(10) << "Total"
         << setw(8) << "Hits"
         << setw(8) << "Misses"
         << setw(12) << "Hit Rate"
         << setw(12) << "Miss Rate"
         << setw(12) << "EMAT" << "\n";
    cout << "  " << string(82, '-') << "\n";

    for (const auto& r : results) {
        cout << "  " << left
             << setw(10) << r.policy
             << setw(10) << r.tlbSize
             << setw(10) << r.totalAccesses
             << setw(8) << r.hits
             << setw(8) << r.misses
             << setw(12) << fixed << setprecision(2) << (r.hitRate * 100) << "%"
             << setw(12) << fixed << setprecision(2) << (r.missRate * 100) << "%"
             << setw(12) << fixed << setprecision(2) << r.emat << "\n";
    }
    cout << "  " << string(82, '=') << "\n";
}

void printBaselineComparison(double ematWithTlb, int bestSize, const string& bestPolicy) {
    double ematNoTlb = MEMORY_ACCESS_TIME;
    double speedup = ematNoTlb / ematWithTlb;

    cout << "\n  " << string(50, '=') << "\n";
    cout << "  BASELINE COMPARISON\n";
    cout << "  " << string(50, '-') << "\n";
    cout << "  " << left << setw(30) << "Case" << setw(20) << "EMAT" << "\n";
    cout << "  " << string(50, '-') << "\n";
    cout << "  " << left << setw(30) << "Without TLB"
         << fixed << setprecision(2) << ematNoTlb << " units\n";
    cout << "  " << left << setw(30)
         << ("With TLB (" + bestPolicy + ", size=" + to_string(bestSize) + ")")
         << fixed << setprecision(2) << ematWithTlb << " units\n";
    cout << "  " << string(50, '-') << "\n";
    cout << "  Speedup: " << fixed << setprecision(2) << speedup << "x\n";
    cout << "  " << string(50, '=') << "\n";
}

void printObservations(const vector<SimResult>& results) {
    cout << "\n  " << string(60, '=') << "\n";
    cout << "  OBSERVATIONS\n";
    cout << "  " << string(60, '-') << "\n";

    double bestEmat = 1e9;
    string bestConfig;
    double worstEmat = 0;
    string worstConfig;

    for (const auto& r : results) {
        string label = r.policy + " (size=" + to_string(r.tlbSize) + ")";
        if (r.emat < bestEmat) { bestEmat = r.emat; bestConfig = label; }
        if (r.emat > worstEmat) { worstEmat = r.emat; worstConfig = label; }
    }

    cout << "  - Best config  : " << bestConfig
         << " with EMAT = " << fixed << setprecision(2) << bestEmat << "\n";
    cout << "  - Worst config : " << worstConfig
         << " with EMAT = " << fixed << setprecision(2) << worstEmat << "\n";

    double fifoAvg = 0, lruAvg = 0;
    int fifoCount = 0, lruCount = 0;
    for (const auto& r : results) {
        if (r.policy == "FIFO") { fifoAvg += r.hitRate; fifoCount++; }
        else { lruAvg += r.hitRate; lruCount++; }
    }
    if (fifoCount > 0) fifoAvg /= fifoCount;
    if (lruCount > 0) lruAvg /= lruCount;

    cout << "  - FIFO avg hit rate: " << fixed << setprecision(2) << (fifoAvg * 100) << "%\n";
    cout << "  - LRU  avg hit rate: " << fixed << setprecision(2) << (lruAvg * 100) << "%\n";

    if (lruAvg > fifoAvg)
        cout << "  - LRU outperforms FIFO on average.\n";
    else if (fifoAvg > lruAvg)
        cout << "  - FIFO outperforms LRU on average.\n";
    else
        cout << "  - FIFO and LRU perform equally on average.\n";

    bool sizeHelps = true;
    for (int i = 1; i < (int)results.size(); i++) {
        if (results[i].policy == results[i - 1].policy &&
            results[i].tlbSize > results[i - 1].tlbSize &&
            results[i].hitRate < results[i - 1].hitRate) {
            sizeHelps = false;
        }
    }
    if (sizeHelps)
        cout << "  - Increasing TLB size generally improves hit rate.\n";
    else
        cout << "  - Increasing TLB size does not always improve hit rate.\n";

    cout << "  " << string(60, '=') << "\n\n";
}

int main() {
    cout << "\n";
    cout << "  " << string(56, '=') << "\n";
    cout << "  |          TLB PERFORMANCE ANALYZER (C++)          |\n";
    cout << "  " << string(56, '=') << "\n\n";

    int pageSize = 10;
    vector<int> addresses = {10, 22, 15, 10, 45, 22, 55, 10, 22, 78,
                             15, 45, 90, 22, 10, 55, 78, 45, 10, 22};
    vector<int> tlbSizes = {2, 4, 8};
    vector<string> policies = {"FIFO", "LRU"};

    cout << "  Configuration\n";
    cout << "  " << string(40, '-') << "\n";
    cout << "  Page size     : " << pageSize << "\n";
    cout << "  Addresses     : " << addresses.size() << " accesses\n";
    cout << "  TLB sizes     : ";
    for (int i = 0; i < (int)tlbSizes.size(); i++) {
        if (i > 0) cout << ", ";
        cout << tlbSizes[i];
    }
    cout << "\n";
    cout << "  Policies      : FIFO, LRU\n";
    cout << "  TLB access    : " << TLB_ACCESS_TIME << " unit\n";
    cout << "  Memory access : " << MEMORY_ACCESS_TIME << " units\n";
    cout << "  " << string(40, '-') << "\n";

    bool showTrace = true;
    SimResult traceResult = runSimulation(addresses, pageSize, 3, "FIFO", showTrace);

    vector<SimResult> allResults;

    for (const string& pol : policies) {
        for (int sz : tlbSizes) {
            SimResult r = runSimulation(addresses, pageSize, sz, pol, false);
            allResults.push_back(r);
        }
    }

    printResultsTable(allResults);

    double bestEmat = 1e9;
    int bestSize = 0;
    string bestPolicy;
    for (const auto& r : allResults) {
        if (r.emat < bestEmat) {
            bestEmat = r.emat;
            bestSize = r.tlbSize;
            bestPolicy = r.policy;
        }
    }

    printBaselineComparison(bestEmat, bestSize, bestPolicy);
    printObservations(allResults);

    return 0;
}
