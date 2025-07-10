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
import whitelist.py

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
        self.whitelisted_users: Set[int] = set()
        self.whitelisted_groups: Set[int] = set()
        self.whitelist_enabled = True
        
        # Load whitelist from file
        self.load_whitelist()
        
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
            'BBRI.JK', 'BMRI.JK', 'BBCA.JK', 'BBNI.JK', 'TLKM.JK',
            'ASII.JK', 'UNVR.JK', 'ICBP.JK', 'KLBF.JK', 'INDF.JK',
            'GGRM.JK', 'SMGR.JK', 'PGAS.JK', 'PTBA.JK', 'ADRO.JK',
            'ITMG.JK', 'ANTM.JK', 'TKIM.JK', 'MEDC.JK', 'PWON.JK'
        ]
        
        self.setup_handlers()
    
    def load_whitelist(self):
        """Load whitelist from JSON file"""
        try:
            if os.path.exists('whitelist.json'):
                with open('whitelist.json', 'r') as f:
                    data = json.load(f)
                    self.whitelisted_users = set(data.get('users', []))
                    self.whitelisted_groups = set(data.get('groups', []))
                    self.whitelist_enabled = data.get('enabled', True)
        except Exception as e:
            logger.error(f"Error loading whitelist: {e}")
    
    def save_whitelist(self):
        """Save whitelist to JSON file"""
        try:
            data = {
                'users': list(self.whitelisted_users),
                'groups': list(self.whitelisted_groups),
                'enabled': self.whitelist_enabled
            }
            with open('whitelist.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving whitelist: {e}")
    
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
            if not self.whitelist_enabled:
                return await func(self, update, context)
            
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
        
        # Whitelist management commands (admin only)
        self.application.add_handler(CommandHandler("whitelist_add_user", self.whitelist_add_user))
        self.application.add_handler(CommandHandler("whitelist_remove_user", self.whitelist_remove_user))
        self.application.add_handler(CommandHandler("whitelist_add_group", self.whitelist_add_group))
        self.application.add_handler(CommandHandler("whitelist_remove_group", self.whitelist_remove_group))
        self.application.add_handler(CommandHandler("whitelist_list", self.whitelist_list))
        self.application.add_handler(CommandHandler("whitelist_enable", self.whitelist_enable))
        self.application.add_handler(CommandHandler("whitelist_disable", self.whitelist_disable))
        self.application.add_handler(CommandHandler("whitelist_status", self.whitelist_status))
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
BOT_TOKEN = "7833221115:AAEvPf5KUY466WaELoJ4p9R1Ag5e8aG8-Lc"  # Ganti dengan token bot Telegram Anda
ADMIN_IDS = [6208519947, 5751902978]  # Ganti dengan Telegram user ID admin

async def main():
    """Main function"""
    if BOT_TOKEN == "7833221115:AAEvPf5KUY466WaELoJ4p9R1Ag5e8aG8-Lc":
        print("❌ Harap masukkan token bot Telegram Anda!")
        print("1. Buat bot baru di @BotFather")
        print("2. Dapatkan token dan ganti BOT_TOKEN di kode")
        print("3. Dapatkan user ID admin dan masukkan ke ADMIN_IDS")
        return
    
    if not ADMIN_IDS or ADMIN_IDS == [6208519947, 5751902978]:
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
