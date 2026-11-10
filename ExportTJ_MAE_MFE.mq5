//+------------------------------------------------------------------+
//|                                             ExportTJ_MAE_MFE.mq5 |
//|  Exporte les positions clôturées avec MAE / MFE pour le          |
//|  Trading Journal Pro (fichier CSV dans le dossier Common\Files). |
//|                                                                  |
//|  MAE = recul maximal contre la position (Max Adverse Excursion)  |
//|  MFE = avancée maximale en faveur (Max Favorable Excursion)      |
//|  Calculées sur les bougies du broker entre l'entrée et la sortie.|
//+------------------------------------------------------------------+
#property copyright "Trading Journal Pro"
#property version   "1.00"
#property script_show_inputs

input int             InpDaysBack  = 365;              // Historique à exporter (jours)
input string          InpFileName  = "TJ_MAE_MFE.csv"; // Nom du fichier (Common\Files)
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M1;        // Unité de mesure des extrêmes

//--- motif de clôture lisible
string ReasonText(const long reason)
  {
   switch((int)reason)
     {
      case DEAL_REASON_SL:     return("SL");
      case DEAL_REASON_TP:     return("TP");
      case DEAL_REASON_SO:     return("STOPOUT");
      case DEAL_REASON_CLIENT: return("MANUEL");
      case DEAL_REASON_MOBILE: return("MANUEL");
      case DEAL_REASON_WEB:    return("MANUEL");
      case DEAL_REASON_EXPERT: return("EA");
     }
   return("AUTRE");
  }

//--- date au format ISO "AAAA-MM-JJ HH:MM:SS"
string IsoTime(const datetime t)
  {
   string s = TimeToString(t, TIME_DATE | TIME_SECONDS);
   StringReplace(s, ".", "-");
   return(s);
  }

//--- l'identifiant est-il déjà dans la liste ?
bool Contains(const ulong &arr[], const int n, const ulong v)
  {
   for(int i = 0; i < n; i++)
      if(arr[i] == v)
         return(true);
   return(false);
  }

//+------------------------------------------------------------------+
void OnStart()
  {
   datetime to   = TimeCurrent();
   datetime from = to - (datetime)((long)InpDaysBack * 86400);
   if(!HistorySelect(from, to))
     {
      Print("HistorySelect a échoué : ", GetLastError());
      return;
     }

//--- 1) identifiants des positions ouvertes dans la période
   ulong ids[];
   int   nIds  = 0;
   int   total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if(tk == 0)
         continue;
      if(HistoryDealGetInteger(tk, DEAL_ENTRY) != DEAL_ENTRY_IN)
         continue;
      ulong pid = (ulong)HistoryDealGetInteger(tk, DEAL_POSITION_ID);
      if(!Contains(ids, nIds, pid))
        {
         ArrayResize(ids, nIds + 1, 1000);
         ids[nIds++] = pid;
        }
     }

   int fh = FileOpen(InpFileName, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ';');
   if(fh == INVALID_HANDLE)
     {
      Print("Ouverture du fichier impossible : ", GetLastError());
      return;
     }
   FileWrite(fh, "position_id", "symbol", "type", "volume", "open_time", "open_price",
             "close_time", "close_price", "sl_open", "tp_open", "sl_close", "tp_close",
             "exit_reason", "profit", "mae_price", "mfe_price", "mae_money", "mfe_money", "timeframe");

   int written = 0, noBars = 0;
//--- 2) une ligne par position clôturée
   for(int p = 0; p < nIds; p++)
     {
      ulong pid = ids[p];
      if(!HistorySelectByPosition(pid))
         continue;

      string   sym = "";
      long     ptype = -1, reason = -1;
      double   vol = 0, openPrice = 0, closePrice = 0, closeVol = 0, profit = 0;
      double   slOpen = 0, tpOpen = 0, slClose = 0, tpClose = 0;
      datetime tOpen = 0, tClose = 0;
      ulong    openOrder = 0;

      int nd = HistoryDealsTotal();
      for(int j = 0; j < nd; j++)
        {
         ulong tk = HistoryDealGetTicket(j);
         if(tk == 0)
            continue;
         long dtype = HistoryDealGetInteger(tk, DEAL_TYPE);
         if(dtype != DEAL_TYPE_BUY && dtype != DEAL_TYPE_SELL)
            continue;
         long entry = HistoryDealGetInteger(tk, DEAL_ENTRY);
         profit += HistoryDealGetDouble(tk, DEAL_PROFIT)
                 + HistoryDealGetDouble(tk, DEAL_COMMISSION)
                 + HistoryDealGetDouble(tk, DEAL_SWAP);
         if(entry == DEAL_ENTRY_IN)
           {
            vol += HistoryDealGetDouble(tk, DEAL_VOLUME);
            if(tOpen == 0)
              {
               sym       = HistoryDealGetString(tk, DEAL_SYMBOL);
               ptype     = (dtype == DEAL_TYPE_BUY) ? 0 : 1;
               tOpen     = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
               openPrice = HistoryDealGetDouble(tk, DEAL_PRICE);
               slOpen    = HistoryDealGetDouble(tk, DEAL_SL);
               tpOpen    = HistoryDealGetDouble(tk, DEAL_TP);
               openOrder = (ulong)HistoryDealGetInteger(tk, DEAL_ORDER);
              }
           }
         else
            if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY || entry == DEAL_ENTRY_INOUT)
              {
               double v  = HistoryDealGetDouble(tk, DEAL_VOLUME);
               double px = HistoryDealGetDouble(tk, DEAL_PRICE);
               if(closeVol + v > 0)
                  closePrice = (closePrice * closeVol + px * v) / (closeVol + v);
               closeVol += v;
               tClose    = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
               reason    = HistoryDealGetInteger(tk, DEAL_REASON);
               double s  = HistoryDealGetDouble(tk, DEAL_SL);
               double t  = HistoryDealGetDouble(tk, DEAL_TP);
               if(s > 0)
                  slClose = s;
               if(t > 0)
                  tpClose = t;
              }
        }
      if(tOpen == 0 || tClose == 0 || sym == "")
         continue;                       // position encore ouverte ou incomplète

      //--- SL / TP initiaux : ordre d'ouverture si le deal ne les porte pas
      if((slOpen == 0 || tpOpen == 0) && openOrder > 0 && HistoryOrderSelect(openOrder))
        {
         if(slOpen == 0)
            slOpen = HistoryOrderGetDouble(openOrder, ORDER_SL);
         if(tpOpen == 0)
            tpOpen = HistoryOrderGetDouble(openOrder, ORDER_TP);
        }

      //--- extrêmes atteints pendant le trade (bougies du broker)
      MqlRates rates[];
      ENUM_TIMEFRAMES tf = InpTimeframe;
      int nb = CopyRates(sym, tf, tOpen, tClose, rates);
      if(nb <= 0 && tf != PERIOD_M5)
        {
         tf = PERIOD_M5;
         nb = CopyRates(sym, tf, tOpen, tClose, rates);
        }
      if(nb <= 0 && tf != PERIOD_H1)
        {
         tf = PERIOD_H1;
         nb = CopyRates(sym, tf, tOpen, tClose, rates);
        }
      double hi = MathMax(openPrice, closePrice);
      double lo = MathMin(openPrice, closePrice);
      for(int k = 0; k < nb; k++)
        {
         if(rates[k].high > hi)
            hi = rates[k].high;
         if(rates[k].low < lo)
            lo = rates[k].low;
        }
      if(nb <= 0)
         noBars++;

      double mae, mfe;
      if(ptype == 0)
        {
         mfe = hi - openPrice;
         mae = openPrice - lo;
        }
      else
        {
         mfe = openPrice - lo;
         mae = hi - openPrice;
        }
      double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
      double tickSize  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
      double perPrice  = (tickSize > 0) ? tickValue / tickSize * vol : 0.0;
      int    dg        = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
      if(dg <= 0)
         dg = 5;

      FileWrite(fh, (string)pid, sym, (ptype == 0 ? "BUY" : "SELL"), DoubleToString(vol, 2),
                IsoTime(tOpen), DoubleToString(openPrice, dg),
                IsoTime(tClose), DoubleToString(closePrice, dg),
                DoubleToString(slOpen, dg), DoubleToString(tpOpen, dg),
                DoubleToString(slClose, dg), DoubleToString(tpClose, dg),
                ReasonText(reason), DoubleToString(profit, 2),
                (nb > 0 ? DoubleToString(mae, dg) : ""), (nb > 0 ? DoubleToString(mfe, dg) : ""),
                (nb > 0 ? DoubleToString(mae * perPrice, 2) : ""), (nb > 0 ? DoubleToString(mfe * perPrice, 2) : ""),
                EnumToString(tf));
      written++;
      if(written % 200 == 0)
         Comment("Export Trading Journal : ", written, " / ", nIds, " positions");
     }
   FileClose(fh);
   Comment("");
   string path = TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\" + InpFileName;
   PrintFormat("Export terminé : %d positions -> %s (%d sans historique de prix)", written, path, noBars);
   Alert(StringFormat("Trading Journal : %d positions exportées.\nFichier : %s", written, path));
  }
//+------------------------------------------------------------------+
