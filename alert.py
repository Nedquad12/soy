import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import pandas as pd
import yfinance as yf
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import pytz
import numpy as np
import json
import os
from collections import defaultdict
from functools import wraps

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class StockVolumeMonitor:
    def __init__(self, bot_token: str, admin_ids: List[int] = None):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.application = Application.builder().token(bot_token).build()
        
        # Admin and whitelist configuration
        self.admin_ids: Set[int] = set(admin_ids) if admin_ids else set()
        
        # Timezone Indonesia
        self.tz = pytz.timezone('Asia/Jakarta')
        
        # Data storage
        self.monitored_groups: List[str] = []
        self.stock_data: Dict[str, Dict] = {}
        self.volume_history: Dict[str, List] = defaultdict(list)
        
        # Trading hours (WIB)
        self.trading_start = 9  # 09:00
        self.trading_end = 16   # 16:00
        
        # Alert settings
        self.volume_threshold = 2.0  # 2x lipat
        self.monitoring_interval = 60  # 1 menit
        self.avg_window_minutes = 120  # 2 jam untuk hitung rata-rata
        
        # Daftar saham populer Indonesia
        self.popular_stocks = [
            'AADI.JK', 'AALI.JK', 'ABBA.JK', 'ABDA.JK', 'ABMM.JK', 'ACES.JK', 'ACRO.JK', 'ACST.JK', 'ADCP.JK', 'ADES.JK', 
            'ADHI.JK', 'ADMF.JK', 'ADMG.JK', 'ADMR.JK', 'ADRO.JK', 'AEGS.JK', 'AGAR.JK', 'AGII.JK', 'AGRO.JK', 
            'AGRS.JK', 'AHAP.JK', 'AIMS.JK', 'AISA.JK', 'AKKU.JK', 'AKPI.JK', 'AKRA.JK', 'AKSI.JK', 'ALDO.JK', 
            'ALII.JK', 'ALKA.JK', 'ALMI.JK', 'ALTO.JK', 'AMAG.JK', 'AMAN.JK', 'AMAR.JK', 'AMFG.JK', 'AMIN.JK', 
            'AMMN.JK', 'AMMS.JK', 'AMOR.JK', 'AMRT.JK', 'ANDI.JK', 'ANJT.JK', 'ANTM.JK', 'APEX.JK', 'APIC.JK', 
            'APII.JK', 'APLI.JK', 'APLN.JK', 'ARCI.JK', 'AREA.JK', 'ARGO.JK', 'ARII.JK', 'ARKA.JK', 'ARKO.JK', 
            'ARMY.JK', 'ARNA.JK', 'ARTA.JK', 'ARTI.JK', 'ARTO.JK', 'ASBI.JK', 'ASDM.JK', 'ASGR.JK', 'ASHA.JK', 
            'ASII.JK', 'ASJT.JK', 'ASLC.JK', 'ASLI.JK', 'ASMI.JK', 'ASPI.JK', 'ASRI.JK', 'ASRM.JK', 'ASSA.JK', 
            'ATAP.JK', 'ATIC.JK', 'ATLA.JK', 'AUTO.JK', 'AVIA.JK', 'AWAN.JK', 'AXIO.JK', 'AYAM.JK', 'AYLS.JK', 
            'BABP.JK', 'BABY.JK', 'BACA.JK', 'BAIK.JK', 'BAJA.JK', 'BALI.JK', 'BANK.JK', 'BAPA.JK', 'BAPI.JK', 
            'BATA.JK', 'BATR.JK', 'BAUT.JK', 'BAYU.JK', 'BBCA.JK', 'BBHI.JK', 'BBKP.JK', 'BBLD.JK', 'BBMD.JK', 
            'BBNI.JK', 'BBRI.JK', 'BBRM.JK', 'BBSI.JK', 'BBSS.JK', 'BBTN.JK', 'BBYB.JK', 'BCAP.JK', 'BCIC.JK', 
            'BCIP.JK', 'BDKR.JK', 'BDMN.JK', 'BEBS.JK', 'BEEF.JK', 'BEER.JK', 'BEKS.JK', 'BELI.JK', 'BELL.JK', 
            'BESS.JK', 'BEST.JK', 'BFIN.JK', 'BGTG.JK', 'BHAT.JK', 'BHIT.JK', 'BIKA.JK', 'BIKE.JK', 'BIMA.JK', 
            'BINA.JK', 'BINO.JK', 'BIPI.JK', 'BIPP.JK', 'BIRD.JK', 'BISI.JK', 'BJBR.JK', 'BJTM.JK', 'BKDP.JK', 
            'BKSL.JK', 'BKSW.JK', 'BLES.JK', 'BLTA.JK', 'BLTZ.JK', 'BLUE.JK', 'BMAS.JK', 'BMBL.JK', 'BMHS.JK', 
            'BMRI.JK', 'BMSR.JK', 'BMTR.JK', 'BNBA.JK', 'BNBR.JK', 'BNGA.JK', 'BNII.JK', 'BNLI.JK', 'BOAT.JK', 
            'BOBA.JK', 'BOGA.JK', 'BOLA.JK', 'BOLT.JK', 'BOSS.JK', 'BPFI.JK', 'BPII.JK', 'BPTR.JK', 'BRAM.JK', 
            'BREN.JK', 'BRIS.JK', 'BRMS.JK', 'BRNA.JK', 'BRPT.JK', 'BRRC.JK', 'BSBK.JK', 'BSDE.JK', 'BSIM.JK', 
            'BSML.JK', 'BSSR.JK', 'BSWD.JK', 'BTEK.JK', 'BTEL.JK', 'BTON.JK', 'BTPN.JK', 'BTPS.JK', 'BUAH.JK', 
            'BUDI.JK', 'BUKA.JK', 'BUKK.JK', 'BULL.JK', 'BUMI.JK', 'BUVA.JK', 'BVIC.JK', 'BWPT.JK', 'BYAN.JK', 
            'CAKK.JK', 'CAMP.JK', 'CANI.JK', 'CARE.JK', 'CARS.JK', 'CASA.JK', 'CASH.JK', 'CASS.JK', 'CBDK.JK', 
            'CBMF.JK', 'CBPE.JK', 'CBRE.JK', 'CBUT.JK', 'CCSI.JK', 'CEKA.JK', 'CENT.JK', 'CFIN.JK', 'CGAS.JK', 
            'CHEM.JK', 'CHIP.JK', 'CINT.JK', 'CITA.JK', 'CITY.JK', 'CLAY.JK', 'CLEO.JK', 'CLPI.JK', 'CMNP.JK', 'CMNT.JK', 
            'CMPP.JK', 'CMRY.JK', 'CNKO.JK', 'CNMA.JK', 'CNTB.JK', 'CNTX.JK', 'COAL.JK', 'COCO.JK', 'COWL.JK', 
            'CPIN.JK', 'CPRI.JK', 'CPRO.JK', 'CRAB.JK', 'CRSN.JK', 'CSAP.JK', 'CSIS.JK', 'CSMI.JK', 'CSRA.JK', 
            'CTBN.JK', 'CTRA.JK', 'CTTH.JK', 'CUAN.JK', 'CYBR.JK', 'DAAZ.JK', 'DADA.JK', 'DART.JK', 'DATA.JK', 
            'DAYA.JK', 'DCII.JK', 'DEAL.JK', 'DEFI.JK', 'DEPO.JK', 'DEWA.JK', 'DEWI.JK', 'DFAM.JK', 'DGIK.JK', 
            'DGNS.JK', 'DGWG.JK', 'DIGI.JK', 'DILD.JK', 'DIVA.JK', 'DKFT.JK', 'DLTA.JK', 'DMAS.JK', 'DMMX.JK', 
            'DMND.JK', 'DNAR.JK', 'DNET.JK', 'DOID.JK', 'DOOH.JK', 'DOSS.JK', 'DPNS.JK', 'DPUM.JK', 'DRMA.JK', 
            'DSFI.JK', 'DSNG.JK', 'DSSA.JK', 'DUCK.JK', 'DUTI.JK', 'DVLA.JK', 'DWGL.JK', 'DYAN.JK', 'EAST.JK', 
            'ECII.JK', 'EDGE.JK', 'EKAD.JK', 'ELIT.JK', 'ELPI.JK', 'ELSA.JK', 'ELTY.JK', 'EMDE.JK', 'EMTK.JK', 
            'ENAK.JK', 'ENRG.JK', 'ENVY.JK', 'ENZO.JK', 'EPAC.JK', 'EPMT.JK', 'ERAA.JK', 'ERAL.JK', 'ERTX.JK', 
            'ESIP.JK', 'ESSA.JK', 'ESTA.JK', 'ESTI.JK', 'ETWA.JK', 'EURO.JK', 'EXCL.JK', 'FAPA.JK', 'FAST.JK', 
            'FASW.JK', 'FILM.JK', 'FIMP.JK', 'FIRE.JK', 'FISH.JK', 'FITT.JK', 'FLMC.JK', 'FMII.JK', 'FOLK.JK', 
            'FOOD.JK', 'FORE.JK', 'FORU.JK', 'FORZ.JK', 'FPNI.JK', 'FUJI.JK', 'FUTR.JK', 'FWCT.JK', 'GAMA.JK', 
            'GDST.JK', 'GDYR.JK', 'GEMA.JK', 'GEMS.JK', 'GGRM.JK', 'GGRP.JK', 'GHON.JK', 'GIAA.JK', 'GJTL.JK', 
            'GLOB.JK', 'GLVA.JK', 'GMFI.JK', 'GMTD.JK', 'GOLD.JK', 'GOLF.JK', 'GOLL.JK', 'GOOD.JK', 'GOTO.JK', 
            'GPRA.JK', 'GPSO.JK', 'GRIA.JK', 'GRPH.JK', 'GRPM.JK', 'GSMF.JK', 'GTBO.JK', 'GTRA.JK',
            'GTSI.JK', 'GULA.JK', 'GUNA.JK', 'GWSA.JK', 'GZCO.JK', 'HADE.JK', 'HAIS.JK', 'HAJJ.JK', 'HALO.JK', 
            'HATM.JK', 'HBAT.JK', 'HDFA.JK', 'HDIT.JK', 'HDTX.JK', 'HEAL.JK', 'HELI.JK', 'HERO.JK', 'HEXA.JK', 
            'HGII.JK', 'HILL.JK', 'HITS.JK', 'HKMU.JK', 'HMSP.JK', 'HOKI.JK', 'HOME.JK', 'HOMI.JK', 'HOPE.JK', 
            'HOTL.JK', 'HRME.JK', 'HRTA.JK', 'HRUM.JK', 'HUMI.JK', 'HYGN.JK', 'IATA.JK', 'IBFN.JK', 'IBOS.JK', 
            'IBST.JK', 'ICBP.JK', 'ICON.JK', 'IDEA.JK', 'IDPR.JK', 'IFII.JK', 'IFSH.JK', 'IGAR.JK', 'IIKP.JK', 
            'IKAI.JK', 'IKAN.JK', 'IKBI.JK', 'IKPM.JK', 'IMAS.JK', 'IMJS.JK', 'IMPC.JK', 'INAF.JK', 'INAI.JK', 
            'INCF.JK', 'INCI.JK', 'INCO.JK', 'INDF.JK', 'INDO.JK', 'INDR.JK', 'INDS.JK', 'INDX.JK', 'INDY.JK', 
            'INET.JK', 'INKP.JK', 'INOV.JK', 'INPC.JK', 'INPP.JK', 'INPS.JK', 'INRU.JK', 'INTA.JK', 'INTD.JK', 
            'INTP.JK', 'IOTF.JK', 'IPAC.JK', 'IPCC.JK', 'IPCM.JK', 'IPOL.JK', 'IPPE.JK', 'IPTV.JK', 'IRRA.JK', 
            'IRSX.JK', 'ISAP.JK', 'ISAT.JK', 'ISEA.JK', 'ISSP.JK', 'ITIC.JK', 'ITMA.JK', 'ITMG.JK', 'JARR.JK', 'JAST.JK', 'JATI.JK', 'JAWA.JK', 
            'JAYA.JK', 'JECC.JK', 'JGLE.JK', 'JIHD.JK', 'JKON.JK', 'JKSW.JK', 'JMAS.JK', 'JPFA.JK', 'JRPT.JK', 
            'JSKY.JK', 'JSMR.JK', 'JSPT.JK', 'JTPE.JK', 'KAEF.JK', 'KAQI.JK', 'KARW.JK', 'KAYU.JK', 'KBAG.JK', 
            'KBLI.JK', 'KBLM.JK', 'KBLV.JK', 'KBRI.JK', 'KDSI.JK', 'KDTN.JK', 'KEEN.JK', 'KEJU.JK', 'KETR.JK', 
            'KIAS.JK', 'KICI.JK', 'KIJA.JK', 'KING.JK', 'KINO.JK', 'KIOS.JK', 'KJEN.JK', 'KKES.JK', 'KKGI.JK', 
            'KLAS.JK', 'KLBF.JK', 'KLIN.JK', 'KMDS.JK', 'KMTR.JK', 'KOBX.JK', 'KOCI.JK', 'KOIN.JK', 'KOKA.JK', 
            'KONI.JK', 'KOPI.JK', 'KOTA.JK', 'KPAL.JK', 'KPAS.JK', 'KPIG.JK', 'KRAH.JK', 'KRAS.JK', 'KREN.JK', 
            'KRYA.JK', 'KSIX.JK', 'KUAS.JK', 'LABA.JK', 'LABS.JK', 'LAJU.JK', 'LAND.JK', 'LAPD.JK', 'LCGP.JK', 'LCKM.JK', 
            'LEAD.JK', 'LFLO.JK', 'LIFE.JK', 'LINK.JK', 'LION.JK', 'LIVE.JK', 'LMAS.JK', 'LMAX.JK', 'LMPI.JK', 
            'LMSH.JK', 'LOPI.JK', 'LPCK.JK', 'LPGI.JK', 'LPIN.JK', 'LPKR.JK', 'LPLI.JK', 'LPPF.JK', 'LPPS.JK', 
            'LRNA.JK', 'LSIP.JK', 'LTLS.JK', 'LUCK.JK', 'LUCY.JK', 'MABA.JK', 'MAGP.JK', 'MAHA.JK', 'MAIN.JK', 
            'MAMI.JK', 'MAMIP.JK', 'MANG.JK', 'MAPA.JK', 'MAPB.JK', 'MAPI.JK', 'MARI.JK', 'MARK.JK', 'MASA.JK',
            'MASB.JK', 'MAXI.JK', 'MAYA.JK', 'MBAP.JK', 'MBMA.JK', 'MBSS.JK', 'MBTO.JK', 'MCAS.JK', 'MCOL.JK', 
            'MCOR.JK', 'MDIA.JK', 'MDIY.JK', 'MDKA.JK', 'MDKI.JK', 'MDLA.JK', 'MDLN.JK', 'MDRN.JK', 'MEDC.JK', 
            'MEDS.JK', 'MEGA.JK', 'MEJA.JK', 'MENN.JK', 'MERK.JK', 'META.JK', 'MFIN.JK', 'MFMI.JK', 'MGLV.JK', 
            'MGNA.JK', 'MGRO.JK', 'MHKI.JK', 'MICE.JK', 'MIDI.JK', 'MIKA.JK', 'MINA.JK', 'MINE.JK', 'MIRA.JK', 
            'MITI.JK', 'MKAP.JK', 'MKNT.JK', 'MKPI.JK', 'MKTR.JK', 'MLBI.JK', 'MLIA.JK', 'MLPL.JK', 'MLPT.JK', 
            'MMIX.JK', 'MMLP.JK','MNCN.JK', 'MOLI.JK', 'MORA.JK', 'MPIX.JK', 'MPMX.JK', 'MPOW.JK', 'MPPA.JK', 'MPRO.JK', 
            'MPXL.JK', 'MRAT.JK', 'MREI.JK', 'MSIE.JK', 'MSIN.JK', 'MSJA.JK', 'MSKY.JK', 'MSTI.JK', 'MTDL.JK', 
            'MTEL.JK', 'MTFN.JK', 'MTLA.JK', 'MTMH.JK', 'MTPS.JK', 'MTRA.JK', 'MTSM.JK', 'MTWI.JK', 'MUTU.JK', 
            'MYOH.JK', 'MYOR.JK', 'MYRX.JK', 'MYRXP.JK', 'MYTX.JK', 'NAIK.JK', 'NANO.JK', 'NASA.JK', 'NASI.JK', 
            'NATO.JK', 'NAYZ.JK', 'NCKL.JK', 'NELY.JK', 'NEST.JK', 'NETV.JK', 'NFCX.JK', 'NICE.JK', 'NICK.JK', 
            'NICL.JK', 'NIKL.JK', 'NINE.JK', 'NIPS.JK', 'NIRO.JK', 'NISP.JK', 'NOBU.JK', 'NPGF.JK', 'NRCA.JK', 
            'NSSS.JK', 'NTBK.JK', 'NUSA.JK', 'NZIA.JK', 'OASA.JK', 'OBAT.JK', 'OBMD.JK', 'OCAP.JK', 'OILS.JK', 
            'OKAS.JK', 'OLIV.JK', 'OMED.JK', 'OMRE.JK', 'OPMS.JK', 'PACK.JK', 'PADA.JK', 'PADI.JK', 'PALM.JK', 
            'PAMG.JK', 'PANI.JK', 'PANR.JK', 'PANS.JK', 'PART.JK', 'PBID.JK', 'PBRX.JK', 'PBSA.JK', 'PCAR.JK', 
            'PDES.JK', 'PDPP.JK', 'PEGE.JK', 'PEHA.JK', 'PEVE.JK', 'PGAS.JK', 'PGEO.JK', 'PGJO.JK', 'PGLI.JK', 
            'PGUN.JK', 'PICO.JK', 'PIPA.JK', 'PJAA.JK', 'PKPK.JK', 'PLAN.JK', 'PLAS.JK', 'PLIN.JK', 'PMJS.JK', 
            'PMMP.JK', 'PNBN.JK', 'PNBS.JK', 'PNGO.JK', 'PNIN.JK', 'PNLF.JK', 'PNSE.JK', 'POLA.JK', 'POLI.JK', 
            'POLL.JK', 'POLU.JK', 'POLY.JK', 'POOL.JK', 'PORT.JK', 'POSA.JK', 'POWR.JK', 'PPGL.JK', 'PPRE.JK', 
            'PPRI.JK', 'PPRO.JK', 'PRAS.JK', 'PRAY.JK', 'PRDA.JK', 'PRIM.JK', 'PSAB.JK', 'PSDN.JK', 'PSGO.JK', 
            'PSKT.JK', 'PSSI.JK', 'PTBA.JK', 'PTDU.JK', 'PTIS.JK', 'PTMP.JK', 'PTMR.JK', 'PTPP.JK', 'PTPS.JK', 
            'PTPW.JK', 'PTRO.JK', 'PTSN.JK', 'PTSP.JK', 'PUDP.JK', 'PURA.JK', 'PURE.JK', 'PURI.JK', 'PWON.JK', 
            'PYFA.JK', 'PZZA.JK', 'RAAM.JK', 'RAFI.JK', 'RAJA.JK', 'RALS.JK', 'RANC.JK', 'RATU.JK', 'RBMS.JK', 
            'RCCC.JK', 'RDTX.JK', 'REAL.JK', 'RELF.JK', 'RELI.JK', 'RGAS.JK', 'RICY.JK', 'RIGS.JK', 'RIMO.JK', 
            'RISE.JK', 'RMKE.JK', 'RMKO.JK', 'ROCK.JK', 'RODA.JK', 'RONY.JK', 'ROTI.JK', 'RSCH.JK', 'RSGK.JK', 
            'RUIS.JK', 'RUNS.JK', 'SAFE.JK', 'SAGE.JK', 'SAME.JK', 'SAMF.JK', 'SAPX.JK', 'SATU.JK', 'SBAT.JK', 'SBMA.JK', 
            'SCCO.JK', 'SCMA.JK', 'SCNP.JK', 'SCPI.JK', 'SDMU.JK', 'SDPC.JK', 'SDRA.JK', 'SEMA.JK', 'SFAN.JK', 
            'SGER.JK', 'SGRO.JK', 'SHID.JK', 'SHIP.JK', 'SICO.JK', 'SIDO.JK', 'SILO.JK', 'SIMA.JK', 'SIMP.JK', 
            'SINI.JK', 'SIPD.JK', 'SKBM.JK', 'SKLT.JK', 'SKRN.JK', 'SKYB.JK', 'SLIS.JK', 'SMAR.JK', 'SMBR.JK', 
            'SMCB.JK', 'SMDM.JK', 'SMDR.JK', 'SMGA.JK', 'SMGR.JK', 'SMIL.JK', 'SMKL.JK', 'SMKM.JK', 'SMLE.JK', 
            'SMMA.JK', 'SMMT.JK', 'SMRA.JK', 'SMRU.JK', 'SMSM.JK', 'SNLK.JK', 'SOCI.JK', 'SOFA.JK', 'SOHO.JK', 
            'SOLA.JK', 'SONA.JK', 'SOSS.JK', 'SOTS.JK', 'SOUL.JK', 'SPMA.JK', 'SPRE.JK', 'SPTO.JK', 'SQMI.JK', 
            'SRAJ.JK', 'SRIL.JK', 'SRSN.JK', 'SRTG.JK', 'SSIA.JK', 'SSMS.JK', 'SSTM.JK', 'STAA.JK', 'STAR.JK', 
            'STRK.JK', 'STTP.JK', 'SUGI.JK', 'SULI.JK', 'SUNI.JK', 'SUPR.JK', 'SURE.JK', 'SURI.JK', 'SWAT.JK', 
            'SWID.JK', 'TALF.JK', 'TAMA.JK', 'TAMU.JK', 'TAPG.JK', 'TARA.JK', 'TAXI.JK', 'TAYS.JK', 'TBIG.JK', 
            'TBLA.JK', 'TBMS.JK', 'TCID.JK', 'TCPI.JK', 'TDPM.JK', 'TEBE.JK', 'TECH.JK', 'TELE.JK', 'TFAS.JK', 
            'TFCO.JK', 'TGKA.JK', 'TGRA.JK', 'TGUK.JK', 'TIFA.JK', 'TINS.JK', 'TIRA.JK', 'TIRT.JK', 'TKIM.JK', 
            'TLDN.JK', 'TLKM.JK', 'TMAS.JK', 'TMPO.JK', 'TNCA.JK', 'TOBA.JK', 'TOOL.JK', 'TOPS.JK', 'TOSK.JK', 
            'TOTL.JK', 'TOTO.JK', 'TOWR.JK', 'TOYS.JK', 'TPIA.JK', 'TPMA.JK', 'TRAM.JK', 'TRGU.JK', 'TRIL.JK', 
            'TRIM.JK', 'TRIN.JK', 'TRIO.JK', 'TRIS.JK', 'TRJA.JK', 'TRON.JK', 'TRST.JK', 'TRUE.JK', 'TRUK.JK', 
            'TRUS.JK', 'TSPC.JK', 'TUGU.JK', 'TYRE.JK', 'UANG.JK', 'UCID.JK', 'UDNG.JK', 'UFOE.JK', 'ULTJ.JK', 
            'UNIC.JK', 'UNIQ.JK', 'UNIT.JK', 'UNSP.JK', 'UNTD.JK', 'UNTR.JK', 'UNVR.JK', 'URBN.JK', 'UVCR.JK', 
            'VAST.JK', 'VERN.JK', 'VICI.JK', 'VICO.JK', 'VINS.JK', 'VISI.JK', 'VIVA.JK', 'VKTR.JK', 'VOKS.JK', 
            'VRNA.JK', 'VTNY.JK', 'WAPO.JK', 'WEGE.JK', 'WEHA.JK', 'WGSH.JK', 'WICO.JK', 'WIDI.JK', 'WIFI.JK', 
            'WIIM.JK', 'WIKA.JK', 'WINE.JK', 'WINR.JK', 'WINS.JK', 'WIRG.JK', 'WMPP.JK', 'WMUU.JK', 'WOMF.JK', 
            'WOOD.JK', 'WOWS.JK', 'WSBP.JK', 'WSKT.JK', 'WTON.JK', 'YELO.JK', 'YOII.JK', 'YPAS.JK', 'YULE.JK', 
            'YUPI.JK', 'ZATA.JK', 'ZBRA.JK', 'ZINC.JK', 'ZONE.JK', 'ZYRX.JK'
            
            
        ]
        
        self.setup_handlers()
        
    def whitelist_required(func):
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id

        # Admins always allowed
            if user_id in self.admin_ids:
                return await func(self, update, context)

        # Groups always allowed
            if chat_id < 0:
                return await func(self, update, context)

        # Allow non-whitelist users for /start and /status
            command = update.message.text.split()[0]
            if command in ["/start", "/status"]:
                return await func(self, update, context)

        # Check if user is in hardcoded whitelist
            if user_id in WHITELIST_IDS:
                return await func(self, update, context)
   
            await update.message.reply_text(
                "❌ Anda tidak memiliki akses untuk perintah ini.\n"
                "Hubungi admin untuk mendapatkan akses."
            )
        return wrapper
 
    def admin_only(func):
        """Decorator to restrict command to admins only"""
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            if user_id not in self.admin_ids:
                await update.message.reply_text("❌ Perintah ini hanya untuk admin!")
                return
            return await func(self, update, context)
        return wrapper
    
    def whitelist_required(func):
        """Decorator to check whitelist before executing command"""
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # Always allow admins
            if user_id in self.admin_ids:
                return await func(self, update, context)
            
            # Check if user or group is whitelisted
            if user_id in self.whitelisted_users or chat_id in self.whitelisted_groups:
                return await func(self, update, context)
            
            await update.message.reply_text(
                "❌ Anda tidak memiliki akses untuk menggunakan bot ini.\n"
                "Hubungi admin untuk mendapatkan akses."
            )
            return
        return wrapper
    
    def setup_handlers(self):
        """Setup command handlers"""
        # Basic commands (with whitelist check)
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("add_stock", self.add_stock_command))
        self.application.add_handler(CommandHandler("remove_stock", self.remove_stock_command))
        self.application.add_handler(CommandHandler("list_stocks", self.list_stocks_command))
        
        self.application.add_handler(CommandHandler("admin_help", self.admin_help_command))
    
    @whitelist_required
    async def start_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.monitored_groups:
            self.monitored_groups.append(chat_id)
            await update.message.reply_text(
                "🚀 Bot Volume Alert Saham Indonesia telah diaktifkan!\n\n"
                "Bot akan memantau volume saham Indonesia (.JK) secara real-time "
                "dan mengirim alert ketika ada volume signifikan.\n\n"
                "Gunakan /help untuk melihat perintah yang tersedia."
            )
        else:
            await update.message.reply_text("Bot sudah aktif di grup ini!")
            
    async def broadcast_message(self, text: str):
       """Kirim pesan ke semua grup dan auto-pin jika di grup"""
       for group_id in self.monitored_groups:
           try:
               message = await self.bot.send_message(
                   chat_id=group_id,
                   text=text,
                   parse_mode='Markdown'
               )
               # Auto pin jika di grup
               if group_id < 0:
                   await self.bot.pin_chat_message(chat_id=group_id, message_id=message.message_id)
           except Exception as e:
               logger.error(f"Gagal kirim ke {group_id}: {e}")

    
    @whitelist_required
    async def help_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_id = update.effective_user.id
        is_admin = user_id in self.admin_ids
        
        help_text = """
📊 *Bot Volume Alert Saham Indonesia*

*Perintah yang tersedia:*
• /start - Aktifkan bot di grup
• /status - Cek status monitoring
• /add_stock [KODE] - Tambah saham untuk dipantau
• /remove_stock [KODE] - Hapus saham dari monitoring
• /list_stocks - Lihat daftar saham yang dipantau

*Contoh penggunaan:*
• /add_stock BBRI.JK
• /remove_stock BBRI.JK

*Fitur:*
• Monitoring real-time volume saham Indonesia
• Alert otomatis ketika volume melonjak 2x lipat
• Hanya aktif saat jam trading (09:00-16:00 WIB)
• Broadcast ke semua grup yang diikuti bot
        """
        
        if is_admin:
            help_text += "\n\n🔧 *Perintah Admin:*\n• /admin_help - Bantuan khusus admin"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def admin_help_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin_help command"""
        user_id = update.effective_user.id
        if user_id not in self.admin_ids:
            await update.message.reply_text("❌ Perintah ini hanya untuk admin!")
            return
        
        admin_help_text = """
🔧 *Perintah Admin - Whitelist Management*

*Manajemen User:*
• /whitelist_add_user [USER_ID] - Tambah user ke whitelist
• /whitelist_remove_user [USER_ID] - Hapus user dari whitelist

*Manajemen Group:*
• /whitelist_add_group [GROUP_ID] - Tambah group ke whitelist
• /whitelist_remove_group [GROUP_ID] - Hapus group dari whitelist

*Kontrol Sistem:*
• /whitelist_enable - Aktifkan sistem whitelist
• /whitelist_disable - Nonaktifkan sistem whitelist
• /whitelist_status - Cek status whitelist
• /whitelist_list - Lihat daftar whitelist

*Contoh penggunaan:*
• /whitelist_add_user 123456789
• /whitelist_add_group -1001234567890
• /whitelist_remove_user 123456789

*Tips:*
• Untuk mendapatkan USER_ID, minta user mengirim pesan ke bot
• Untuk GROUP_ID, gunakan bot di grup dan lihat log
• Admin selalu memiliki akses penuh
        """
        
        await update.message.reply_text(admin_help_text, parse_mode='Markdown')
    
    @admin_only
    async def whitelist_add_user(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Add user to whitelist"""
        if not context.args:
            await update.message.reply_text(
                "Gunakan: /whitelist_add_user [USER_ID]\n"
                "Contoh: /whitelist_add_user 123456789"
            )
            return
        
        try:
            user_id = int(context.args[0])
            self.whitelisted_users.add(user_id)
            self.save_whitelist()
            await update.message.reply_text(f"✅ User {user_id} berhasil ditambahkan ke whitelist!")
        except ValueError:
            await update.message.reply_text("❌ USER_ID harus berupa angka!")
    
    @admin_only
    async def whitelist_remove_user(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Remove user from whitelist"""
        if not context.args:
            await update.message.reply_text(
                "Gunakan: /whitelist_remove_user [USER_ID]\n"
                "Contoh: /whitelist_remove_user 123456789"
            )
            return
        
        try:
            user_id = int(context.args[0])
            if user_id in self.whitelisted_users:
                self.whitelisted_users.remove(user_id)
                self.save_whitelist()
                await update.message.reply_text(f"✅ User {user_id} berhasil dihapus dari whitelist!")
            else:
                await update.message.reply_text(f"⚠️ User {user_id} tidak ada dalam whitelist!")
        except ValueError:
            await update.message.reply_text("❌ USER_ID harus berupa angka!")
    
    @admin_only
    async def whitelist_add_group(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Add group to whitelist"""
        if not context.args:
            # If no argument, use current group
            group_id = update.effective_chat.id
            if group_id > 0:  # Private chat
                await update.message.reply_text(
                    "Gunakan: /whitelist_add_group [GROUP_ID]\n"
                    "Atau gunakan perintah ini di grup yang ingin ditambahkan"
                )
                return
        else:
            try:
                group_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ GROUP_ID harus berupa angka!")
                return
        
        self.whitelisted_groups.add(group_id)
        self.save_whitelist()
        await update.message.reply_text(f"✅ Group {group_id} berhasil ditambahkan ke whitelist!")
    
    @admin_only
    async def whitelist_remove_group(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Remove group from whitelist"""
        if not context.args:
            await update.message.reply_text(
                "Gunakan: /whitelist_remove_group [GROUP_ID]\n"
                "Contoh: /whitelist_remove_group -1001234567890"
            )
            return
        
        try:
            group_id = int(context.args[0])
            if group_id in self.whitelisted_groups:
                self.whitelisted_groups.remove(group_id)
                self.save_whitelist()
                await update.message.reply_text(f"✅ Group {group_id} berhasil dihapus dari whitelist!")
            else:
                await update.message.reply_text(f"⚠️ Group {group_id} tidak ada dalam whitelist!")
        except ValueError:
            await update.message.reply_text("❌ GROUP_ID harus berupa angka!")
    
    @admin_only
    async def whitelist_list(self, update, context: ContextTypes.DEFAULT_TYPE):
        """List all whitelisted users and groups"""
        status = "✅ Aktif" if self.whitelist_enabled else "❌ Nonaktif"
        
        text = f"📋 *Daftar Whitelist*\n\n"
        text += f"🔧 Status: {status}\n"
        text += f"👥 Admin: {len(self.admin_ids)}\n"
        text += f"👤 Users: {len(self.whitelisted_users)}\n"
        text += f"💬 Groups: {len(self.whitelisted_groups)}\n\n"
        
        if self.whitelisted_users:
            text += "*Whitelisted Users:*\n"
            for user_id in list(self.whitelisted_users)[:10]:  # Limit to 10
                text += f"• {user_id}\n"
            if len(self.whitelisted_users) > 10:
                text += f"• ... dan {len(self.whitelisted_users) - 10} lainnya\n"
        
        if self.whitelisted_groups:
            text += "\n*Whitelisted Groups:*\n"
            for group_id in list(self.whitelisted_groups)[:10]:  # Limit to 10
                text += f"• {group_id}\n"
            if len(self.whitelisted_groups) > 10:
                text += f"• ... dan {len(self.whitelisted_groups) - 10} lainnya\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    @admin_only
    async def whitelist_enable(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Enable whitelist system"""
        self.whitelist_enabled = True
        self.save_whitelist()
        await update.message.reply_text("✅ Sistem whitelist telah diaktifkan!")
    
    @admin_only
    async def whitelist_disable(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Disable whitelist system"""
        self.whitelist_enabled = False
        self.save_whitelist()
        await update.message.reply_text("❌ Sistem whitelist telah dinonaktifkan!")
    
    @admin_only
    async def whitelist_status(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Show whitelist status"""
        status = "✅ Aktif" if self.whitelist_enabled else "❌ Nonaktif"
        
        text = f"""
📊 *Status Whitelist*

🔧 Status: {status}
👥 Admin: {len(self.admin_ids)}
👤 Whitelisted Users: {len(self.whitelisted_users)}
💬 Whitelisted Groups: {len(self.whitelisted_groups)}

*Keterangan:*
• Admin selalu memiliki akses penuh
• Jika whitelist nonaktif, semua user bisa menggunakan bot
• Jika whitelist aktif, hanya user/group yang terdaftar yang bisa menggunakan bot
        """
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    @whitelist_required
    async def status_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        now = datetime.now(self.tz)
        is_trading_hours = self.trading_start <= now.hour < self.trading_end
        
        status_text = f"""
📈 *Status Bot Volume Alert*

⏰ Waktu: {now.strftime('%H:%M:%S WIB')}
📊 Jam Trading: {'✅ Aktif' if is_trading_hours else '❌ Tutup'}
🔍 Saham Dipantau: {len(self.popular_stocks)}
📢 Grup Terdaftar: {len(self.monitored_groups)}
🎯 Threshold Alert: {self.volume_threshold}x lipat
        """
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    @whitelist_required
    async def add_stock_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_stock command"""
        if not context.args:
            await update.message.reply_text("Gunakan: /add_stock [KODE_SAHAM]\nContoh: /add_stock BBRI.JK")
            return
        
        stock_code = context.args[0].upper()
        if not stock_code.endswith('.JK'):
            stock_code += '.JK'
        
        if stock_code not in self.popular_stocks:
            self.popular_stocks.append(stock_code)
            await update.message.reply_text(f"✅ Saham {stock_code} berhasil ditambahkan ke monitoring!")
        else:
            await update.message.reply_text(f"⚠️ Saham {stock_code} sudah ada dalam monitoring!")
    
    @whitelist_required
    async def remove_stock_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remove_stock command"""
        if not context.args:
            await update.message.reply_text("Gunakan: /remove_stock [KODE_SAHAM]\nContoh: /remove_stock BBRI.JK")
            return
        
        stock_code = context.args[0].upper()
        if not stock_code.endswith('.JK'):
            stock_code += '.JK'
        
        if stock_code in self.popular_stocks:
            self.popular_stocks.remove(stock_code)
            await update.message.reply_text(f"✅ Saham {stock_code} berhasil dihapus dari monitoring!")
        else:
            await update.message.reply_text(f"⚠️ Saham {stock_code} tidak ditemukan dalam monitoring!")
    
    @whitelist_required
    async def list_stocks_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_stocks command"""
        if not self.popular_stocks:
            await update.message.reply_text("Tidak ada saham yang dipantau saat ini.")
            return
        
        stocks_text = "📊 *Daftar Saham yang Dipantau:*\n\n"
        for i, stock in enumerate(self.popular_stocks, 1):
            stocks_text += f"{i}. {stock}\n"
        
        await update.message.reply_text(stocks_text, parse_mode='Markdown')
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        now = datetime.now(self.tz)
        return self.trading_start <= now.hour < self.trading_end
    
    def get_stock_data(self, symbol: str) -> Optional[Dict]:
        """Get real-time stock data"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get intraday data (1 minute intervals)
            data = ticker.history(period="1d", interval="1m")
            
            if data.empty:
                return None
            
            # Get latest data
            latest = data.iloc[-1]
            
            return {
                'symbol': symbol,
                'price': latest['Close'],
                'volume': latest['Volume'],
                'timestamp': data.index[-1],
                'high': latest['High'],
                'low': latest['Low'],
                'open': latest['Open']
            }
        except Exception as e:
            logger.error(f"Error getting data for {symbol}: {e}")
            return None
    
    def calculate_average_volume(self, symbol: str) -> float:
        """Calculate average volume for the specified time window"""
        if symbol not in self.volume_history:
            return 0
        
        history = self.volume_history[symbol]
        if len(history) < 2:
            return 0
        
        # Get volumes from last 2 hours
        cutoff_time = datetime.now(self.tz) - timedelta(minutes=self.avg_window_minutes)
        recent_volumes = [
            vol for timestamp, vol in history 
            if timestamp >= cutoff_time
        ]
        
        if not recent_volumes:
            return 0
        
        return np.mean(recent_volumes)
    
    def should_alert(self, symbol: str, current_volume: float) -> bool:
        """Check if we should send an alert"""
        
        if current_volume < 90000:
           return False
    
        avg_volume = self.calculate_average_volume(symbol)
        
        if avg_volume == 0:
            return False
        
        volume_ratio = current_volume / avg_volume
        return volume_ratio >= self.volume_threshold
    
    async def send_volume_alert(self, symbol: str, data: Dict, volume_ratio: float):
        """Send volume alert to all monitored groups"""
        now = datetime.now(self.tz)
        
        # Format pesan alert
        stock_name = symbol.replace('.JK', '')
        message = f"""
🚨 *VOLUME ALERT* 🚨

📊 {stock_name}
📈 Kenaikan volume {volume_ratio:.1f}x lipat pada jam {now.strftime('%H:%M')} WIB
💰 Last Price: {data['price']:,.0f}
📊 Volume: {data['volume']:,.0f}
🕐 Timestamp: {now.strftime('%d/%m/%Y %H:%M:%S')}

#VolumeAlert #{stock_name}
        """
        
        # Kirim ke semua grup yang terdaftar
        for group_id in self.monitored_groups:
            try:
                await self.bot.send_message(
                    chat_id=group_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error sending alert to {group_id}: {e}")
    
    async def monitor_stocks(self):
        """Main monitoring loop"""
        while True:
            try:
                if not self.is_trading_hours():
                    logger.info("Outside trading hours, sleeping...")
                    await asyncio.sleep(300)  # 5 menit saat tutup
                    continue
                
                logger.info(f"Monitoring {len(self.popular_stocks)} stocks...")
                
                for symbol in self.popular_stocks:
                    try:
                        data = self.get_stock_data(symbol)
                        
                        if data is None:
                            continue
                        
                        # Store volume history
                        current_time = datetime.now(self.tz)
                        self.volume_history[symbol].append((current_time, data['volume']))
                        
                        # Keep only recent history (last 4 hours)
                        cutoff_time = current_time - timedelta(hours=4)
                        self.volume_history[symbol] = [
                            (ts, vol) for ts, vol in self.volume_history[symbol]
                            if ts >= cutoff_time
                        ]
                        
                        # Check if we should alert
                        if self.should_alert(symbol, data['volume']):
                            avg_volume = self.calculate_average_volume(symbol)
                            volume_ratio = data['volume'] / avg_volume
                            
                            logger.info(f"Volume alert for {symbol}: {volume_ratio:.1f}x")
                            await self.send_volume_alert(symbol, data, volume_ratio)
                        
                        # Store latest data
                        self.stock_data[symbol] = data
                        
                    except Exception as e:
                        logger.error(f"Error monitoring {symbol}: {e}")
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def run(self):
        """Run the bot"""
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(self.monitor_stocks())
        
        # Start polling
        await self.application.updater.start_polling()
        
        logger.info("Bot started successfully!")
        
        try:
            await monitor_task
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
        finally:
            await self.application.stop()

# Configuration
BOT_TOKEN = "7833221115:AAF9v8eVPM7x3rmuHF5ErSYivEnOwnk1t1c"  # Ganti dengan token bot Telegram Anda
ADMIN_IDS = [6208519947, 5751902978]  # Ganti dengan Telegram user ID admin
WHITELIST_IDS = [6208519947, 5751902978]  # ID user yang boleh akses penuh


async def main():
    """Main function"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Harap masukkan token bot Telegram Anda!")
        print("1. Buat bot baru di @BotFather")
        print("2. Dapatkan token dan ganti BOT_TOKEN di kode")
        print("3. Dapatkan user ID admin dan masukkan ke ADMIN_IDS")
        return
    
    if not ADMIN_IDS or ADMIN_IDS == [123456789, 987654321]:
        print("❌ Harap masukkan user ID admin di ADMIN_IDS!")
        print("Cara mendapatkan user ID:")
        print("1. Chat ke @userinfobot")
        print("2. Masukkan user ID ke dalam list ADMIN_IDS")
        return
    
    bot = StockVolumeMonitor(BOT_TOKEN, ADMIN_IDS)
    await bot.run()

if __name__ == "__main__":
    # Install required packages
    print("🚀 Starting Telegram Stock Volume Monitor Bot...")
    print("📊 Monitoring Indonesian stocks (.JK) for volume alerts...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
