from typing import List, Optional
from datetime import datetime
from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.blog import BlogPost

class BlogService(CRUDService[BlogPost]):
    def __init__(self):
        super().__init__("blog_posts", DB("rasbhari"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS blog_posts (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        slug VARCHAR(255) NOT NULL UNIQUE,
                        content TEXT NOT NULL,
                        tags TEXT[],
                        status VARCHAR(50) DEFAULT 'draft',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.db.conn.commit()

    def get_by_slug(self, slug: str) -> Optional[BlogPost]:
        return self.find_one_by_field("slug", slug)

    def get_published(self) -> List[BlogPost]:
        return self.find_all(filters={"status": "published"}, sort_by={"created_at": "DESC"})

    def _to_tuple(self, obj: BlogPost) -> tuple:
        return (
            obj.title, obj.slug, obj.content, obj.tags,
            obj.status, obj.created_at, obj.updated_at
        )

    def _to_object(self, row: tuple) -> BlogPost:
        return BlogPost(
            id=row[0], title=row[1], slug=row[2], content=row[3],
            tags=row[4] if row[4] else [], status=row[5],
            created_at=row[6], updated_at=row[7]
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["title", "slug", "content", "tags", "status", "created_at", "updated_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["title", "slug", "content", "tags", "status", "created_at", "updated_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "title", "slug", "content", "tags", "status", "created_at", "updated_at"]
