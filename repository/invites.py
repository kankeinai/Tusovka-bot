import logging
from db import Database
from datetime import datetime

class InviteRepository:
    async def init(self, db: Database):
        self.db = db
        """Initialize the invites table if it doesn't exist"""
        try:
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS invites (
                    id SERIAL PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    created_by BIGINT NOT NULL,
                    max_uses INT NOT NULL DEFAULT 1,
                    current_uses INT NOT NULL DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (created_by) REFERENCES tg_user(id)
                )
            """)
            logging.info("Invites table initialized")
        except Exception as e:
            logging.error(f"Failed to initialize invites table: {e}")
    
    async def create_invite(self, code: str, created_by: int, max_uses: int, expires_at: datetime = None) -> bool:
        """Create a new invite code"""
        try:
            await self.db.execute("""
                INSERT INTO invites (code, created_by, max_uses, expires_at) 
                VALUES ($1, $2, $3, $4)
            """, code, created_by, max_uses, expires_at)
            logging.info(f"Created invite code: {code} with {max_uses} uses")
            return True
        except Exception as e:
            logging.error(f"Failed to create invite: {e}")
            return False
    
    async def get_invite(self, code: str):
        """Get an invite by code"""
        try:
            return await self.db.fetchrow("""
                SELECT * FROM invites WHERE code = $1 AND is_active = TRUE
            """, code)
        except Exception as e:
            logging.error(f"Failed to get invite: {e}")
            return None
    
    async def use_invite(self, code: str) -> bool:
        """Use an invite code (increment current_uses)"""
        try:
            result = await self.db.execute("""
                UPDATE invites 
                SET current_uses = current_uses + 1 
                WHERE code = $1 AND is_active = TRUE 
                AND (expires_at IS NULL OR expires_at > NOW())
                AND current_uses < max_uses
                RETURNING id
            """, code)
            
            if result:
                # Check if we've reached max uses
                invite = await self.get_invite(code)
                if invite and invite['current_uses'] >= invite['max_uses']:
                    await self.deactivate_invite(code)
                
                logging.info(f"Used invite code: {code}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to use invite: {e}")
            return False
    
    async def deactivate_invite(self, code: str) -> bool:
        """Deactivate an invite code"""
        try:
            await self.db.execute("""
                UPDATE invites SET is_active = FALSE WHERE code = $1
            """, code)
            logging.info(f"Deactivated invite code: {code}")
            return True
        except Exception as e:
            logging.error(f"Failed to deactivate invite: {e}")
            return False
    
    async def get_invites_by_creator(self, created_by: int):
        """Get all invites created by a specific user"""
        try:
            return await self.db.fetch("""
                SELECT * FROM invites 
                WHERE created_by = $1 
                ORDER BY created_at DESC
            """, created_by)
        except Exception as e:
            logging.error(f"Failed to get invites by creator: {e}")
            return []
    
    async def get_active_invites(self):
        """Get all active invites"""
        try:
            return await self.db.fetch("""
                SELECT * FROM invites 
                WHERE is_active = TRUE 
                AND (expires_at IS NULL OR expires_at > NOW())
                AND current_uses < max_uses
                ORDER BY created_at DESC
            """)
        except Exception as e:
            logging.error(f"Failed to get active invites: {e}")
            return []
    
    async def is_valid_invite(self, code: str) -> bool:
        """Check if an invite code is valid and can be used"""
        try:
            result = await self.db.fetchrow("""
                SELECT id, created_by FROM invites 
                WHERE code = $1 
                AND is_active = TRUE 
                AND (expires_at IS NULL OR expires_at > NOW())
                AND current_uses < max_uses
            """, code)
            return result or None
        except Exception as e:
            logging.error(f"Failed to check invite validity: {e}")
            return False 