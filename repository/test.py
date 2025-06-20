import logging
from db import Database
from datetime import datetime, timedelta
from settings import get_test_time_limit

class TestRepository:
    async def init(self, db: Database):
        self.db = db
        """Initialize the test table if it doesn't exist"""
        try:
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS tests (
                    id SERIAL PRIMARY KEY,
                    test_type TEXT NOT NULL,
                    test_level TEXT NOT NULL DEFAULT 'intermediate' CHECK (test_level IN ('basic', 'intermediate', 'advanced')),
                    user_id BIGINT NOT NULL,
                    topic TEXT NOT NULL,
                    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    finished_at TIMESTAMP WITH TIME ZONE,
                    finished BOOLEAN DEFAULT FALSE,
                    response TEXT DEFAULT NULL,
                    grade INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES tg_user(id)
                )
            """)
            logging.info("Tests table initialized")
        except Exception as e:
            logging.error(f"Failed to initialize tests table: {e}")
    
    async def create_test(self, test_type: str, user_id: int, topic: str, test_level: str) -> int:
        """Create a new test session"""
        try:
            result = await self.db.fetchrow("""
                INSERT INTO tests (test_type, user_id, topic, test_level) 
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, test_type, user_id, topic, test_level)
            
            test_id = result['id']
            logging.info(f"Created test session: {test_id} for user {user_id}")
            return test_id
            
        except Exception as e:
            logging.error(f"Failed to create test: {e}")
            return None
    
    async def get_active_test(self, user_id: int) -> dict:
        """Get the user's active (unfinished) test"""
        try:
            return await self.db.fetchrow("""
                SELECT * FROM tests 
                WHERE user_id = $1 AND finished = FALSE
                ORDER BY started_at DESC
                LIMIT 1
            """, user_id)
        except Exception as e:
            logging.error(f"Failed to get active test: {e}")
            return None
    
    async def finish_test(self, test_id: int) -> bool:
        """Finish a test by adding response and setting finished=True"""
        try:
            await self.db.execute("""
                UPDATE tests 
                SET finished = TRUE, 
                    finished_at = NOW()
                WHERE id = $1
            """,  test_id)
            
            logging.info(f"Finished test: {test_id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to finish test: {e}")
            return False
    
    async def get_test(self, test_id: int) -> dict:
        """Get a specific test by ID"""
        try:
            return await self.db.fetchrow("""
                SELECT * FROM tests WHERE id = $1
            """, test_id)
        except Exception as e:
            logging.error(f"Failed to get test: {e}")
            return None
    
    async def get_user_tests(self, user_id: int, limit: int = 10) -> list:
        """Get user's test history"""
        try:
            return await self.db.fetch("""
                SELECT * FROM tests 
                WHERE user_id = $1 
                ORDER BY started_at DESC 
                LIMIT $2
            """, user_id, limit)
        except Exception as e:
            logging.error(f"Failed to get user tests: {e}")
            return []
    
    async def cancel_active_test(self, user_id: int) -> bool:
        """Cancel user's active test"""
        try:
            result = await self.db.execute("""
                UPDATE tests 
                SET finished = TRUE, 
                    finished_at = NOW()
                WHERE user_id = $1 AND finished = FALSE
            """, user_id)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to cancel active test: {e}")
            return False
    
    async def check_and_cancel_expired_tests(self) -> int:
        """Check for expired tests and cancel them. Returns number of cancelled tests."""
        try:
            # Get all active tests
            active_tests = await self.db.fetch("""
                SELECT id, test_type, started_at FROM tests 
                WHERE finished = FALSE
            """)
            
            cancelled_count = 0
            current_time = datetime.now()
            
            for test in active_tests:
                test_type = test['test_type']
                started_at = test['started_at']
                time_limit_minutes = get_test_time_limit(test_type)
                
                # Calculate if test has expired
                time_elapsed = current_time - started_at
                if time_elapsed.total_seconds() > (time_limit_minutes * 60):
                    # Test has expired, cancel it
                    await self.db.execute("""
                        UPDATE tests 
                        SET finished = TRUE, 
                            finished_at = NOW(),
                            response = 'AUTO_CANCELLED: Time limit exceeded'
                        WHERE id = $1
                    """, test['id'])
                    
                    cancelled_count += 1
                    logging.info(f"Auto-cancelled expired test {test['id']} (type: {test_type})")
            
            return cancelled_count
            
        except Exception as e:
            logging.error(f"Failed to check expired tests: {e}")
            return 0
    
    async def get_remaining_time(self, test_id: int) -> int:
        """Get remaining time in minutes for a test. Returns negative if expired."""
        try:
            test = await self.get_test(test_id)
            if not test or test['finished']:
                return 0
            
            test_type = test['test_type']
            started_at = test['started_at']
            time_limit_minutes = get_test_time_limit(test_type)
            
            current_time = datetime.now()
            time_elapsed = current_time - started_at
            remaining_seconds = (time_limit_minutes * 60) - time_elapsed.total_seconds()
            
            return max(0, int(remaining_seconds // 60))
            
        except Exception as e:
            logging.error(f"Failed to get remaining time: {e}")
            return 0
    
    async def is_test_expired(self, test_id: int) -> bool:
        """Check if a specific test has expired."""
        try:
            test = await self.get_test(test_id)
            if not test or test['finished']:
                return False
            
            test_type = test['test_type']
            started_at = test['started_at']
            time_limit_minutes = get_test_time_limit(test_type)
            
            current_time = datetime.now()
            time_elapsed = current_time - started_at
            
            return time_elapsed.total_seconds() > (time_limit_minutes * 60)
            
        except Exception as e:
            logging.error(f"Failed to check if test expired: {e}")
            return False
    
    async def update_last_response(self, test_id: int, response: str) -> bool:
        """Update the last response for a test without finishing it."""
        try:
            await self.db.execute("""
                UPDATE tests 
                SET response = $1
                WHERE id = $2 AND finished = FALSE
            """, response, test_id)
            
            logging.info(f"Updated last response for test {test_id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to update last response: {e}")
            return False 