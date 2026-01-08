import re
import json
import logging
import requests
from uuid import UUID
from fastapi import HTTPException
from src.app.core.config import settings
from typing import Dict, List, Optional, Union
from supabase import create_client, Client, StorageException

logger = logging.getLogger(__name__)


def sanitize_key(key):
    # Replace spaces with underscores
    key = key.replace(" ", "_")
    # Remove or replace other potentially problematic characters (e.g., apostrophes, colons)
    # This regex keeps alphanumeric characters, underscores, hyphens, and forward slashes
    key = re.sub(r'[^a-zA-Z0-9_/.-]', '', key)
    return key


class SupabaseService:
    """Unified Supabase service with general CRUD operations"""

    def __init__(self):
        logger.debug("Initializing SupabaseService...")
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        self.bucket = settings.SUPABASE_BUCKET
        logger.debug(f"SupabaseService initialized with bucket: {self.bucket}")

    async def create(
        self,
        table: str,
        data: Dict
    ) -> Dict:
        """Create a new record in the specified table"""
        try:
            logger.debug(f"Supabase CREATE in {table}: {data}")
            response = self.client.table(table).insert(data).execute()
            if not response.data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to create record in {table}"
                )
            return response.data[0]
        except Exception as e:
            logger.error(
                f"Supabase CREATE error in {table}: {str(e)}", exc_info=True)
            raise

    async def get(
        self,
        table: str,
        filters: Dict[str, Union[str, int, bool, UUID, list[UUID]]] = {},
        columns: Optional[List[str]] = None,
        null_columns: List[str] = [],
        not_null_columns: List[str] = [],
        order_by: Optional[str] = None,
        ascending: bool = True
    ) -> Optional[Dict]:
        """Get a single record matching the filters"""
        try:
            logger.debug(f"Supabase GET in {table} with filters: {filters}")
            if not columns:  # Check if columns is None or an empty list
                select_columns = "*"
            else:
                # Convert list of columns to comma-separated string
                select_columns = ", ".join(columns)

            query = self.client.table(table).select(select_columns)

            for key, value in filters.items():
                if isinstance(value, list):
                    query = query.in_(key, value)
                else:
                    query = query.eq(key, value)

            # Handle null columns
            for column in null_columns:
                query = query.is_(column, None)

            # Handle not null columns
            for column in not_null_columns:
                query = query.not_(column, None)

            # Handle ordering
            if order_by:
                query = query.order(order_by)
            else:
                # If no order_by is specified, default to 'created_at' descending
                # This assumes 'created_at' column exists in the table and is a timestamp.
                query = query.order('created_at',  desc=True)

            response = query.execute()

            if not response.data:
                logger.debug(
                    f"No records found in {table} for filters {filters}")
                return None

            # Handle specific cases for resources and jobs
            if table == 'resources':
                try:
                    resource = response.data[0]
                    # Fetch JSON from public URL
                    logger.debug(
                        f"Fetching resource content from {resource['resource_url']}")
                    response = requests.get(resource['resource_url'])
                    response.raise_for_status()  # Raise an exception for HTTP errors
                    # Parse the JSON content
                    resource['content'] = response.json()
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch content for resource {resource.get('id')}: {e}")
                    resource['content'] = {}
                    resource['error'] = str(e)
                finally:
                    return resource
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(
                f"Supabase GET error in {table}: {str(e)}", exc_info=True)
            raise

    async def get_all(
        self,
        table: str,
        filters: Dict[str, Union[str, int, bool, UUID, list[UUID]]] = {},
        columns: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        null_columns: List[str] = [],
        not_null_columns: List[str] = [],
        order_by: Optional[str] = None,
        ascending: bool = True
    ) -> List[Dict]:
        """
        Get all records matching the filters, including null column checks,
        ordering the results, and specifying columns as a list.
        If columns is None or an empty list, select all columns (*).
        """

        if not columns:  # Check if columns is None or an empty list
            select_columns = "*"
        else:
            # Convert list of columns to comma-separated string
            select_columns = ", ".join(columns)

        query = self.client.table(table).select(select_columns)

        for key, value in filters.items():
            if isinstance(value, list):
                query = query.in_(key, value)
            else:
                query = query.eq(key, value)

        # Handle null columns
        for column in null_columns:
            query = query.is_(column, None)

        # Handle not null columns
        for column in not_null_columns:
            query = query.not_(column, None)

        # Handle ordering
        if order_by:
            query = query.order(order_by, desc=not ascending)

        query = query.order('created_at').range(
            offset, offset + limit - 1)
        response = query.execute()
        return response.data

    async def update(
        self,
        table: str,
        filters: Dict[str, Union[str, int, bool, UUID]],
        updates: Dict
    ) -> Dict:
        """Update records matching the filters"""
        try:
            logger.debug(
                f"Supabase UPDATE in {table} with filters {filters}: {updates}")
            query = self.client.table(table).update(updates)
            for key, value in filters.items():
                query = query.eq(key, value)
            response = query.execute()
            if not response.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No records found in {table} matching filters"
                )
            return response.data[0]
        except Exception as e:
            logger.error(
                f"Supabase UPDATE error in {table}: {str(e)}", exc_info=True)
            raise

    async def delete(
        self,
        table: str,
        filters: Dict[str, Union[str, int, bool, UUID]],
        user_id: Optional[str] = None,
        hard_delete: bool = False
    ) -> Dict[str, str]:
        """
        Delete records matching the filters
        """
        try:
            logger.debug(
                f"Supabase DELETE in {table} (hard={hard_delete}) with filters: {filters}")
            if hard_delete:
                # Perform hard delete
                query = self.client.table(table).delete()
            else:
                # Perform soft delete
                query = self.client.table(table).update(
                    {"deleted_at": "now()", "deleted_by": user_id})

            # Apply all filters
            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.execute()
            if not response.data:
                logger.warning(
                    f"No records found in {table} to delete with filters {filters}")
                return {"message": f"No records found in {table} matching filters"}

            delete_type = "permanently deleted" if hard_delete else "deleted"
            logger.info(f"Successfully {delete_type} records from {table}")
            return {"message": f"Records {delete_type} successfully from {table}"}
        except Exception as e:
            logger.error(
                f"Supabase DELETE error in {table}: {str(e)}", exc_info=True)
            raise

    def upload_file_to_storage(
            self,
            resource_path: str,
            user_id: str = None,
            resource_type: str = None,
            table_id: str = None,
            project_id: str = None
    ) -> str:
        """
        Upload a file to Supabase Storage and return its public URL.

        Args:
            resource_path: Local path to the file
            user_id: User ID who owns the resource
            resource_type: Type of resource (video, document, image, etc.)
            table_id: ID of the related table (program_id, module_id, topic_id, etc.)

        Returns:
            Public URL of the uploaded file
        """

        # Upload path in storage
        upload_path = ""
        if project_id:
            upload_path += f"{project_id}/"
        elif user_id:
            upload_path += f"{user_id}/"
        if table_id:
            upload_path += f"{table_id}/"
        if resource_type:
            upload_path += f"{resource_type}/"
        # set the file name
        file_name = resource_path.split("/")[-1]
        upload_path += sanitize_key(file_name)
        if upload_path.endswith("/"):
            upload_path = upload_path[:-1]

        # Check if file exists and upload/update accordingly
        try:
            self.client.storage.from_(self.bucket).upload(
                upload_path, resource_path)
        except StorageException:
            print("Resource already exists")
            # Update resource in supabase storage
            self.client.storage.from_(self.bucket).update(
                upload_path, resource_path)

        # Get bucket url
        resource_url = self.client.storage.from_(
            self.bucket).get_public_url(upload_path)

        return resource_url

    def upload_resource(
            self,
            resource_path: str,
            table_id: str,
            user_id: str,
            project_id: str = None,
            resource_type: str = None,
            resource_index: Optional[int] = None,
            language: Optional[str] = "english"
    ):
        """
        Upload a file to Supabase Storage and create a resource record.

        Args:
            resource_path: Local path to the file
            table_id: ID of the related table (program_id, module_id, topic_id, etc.)
            user_id: User ID who owns the resource
            resource_type: Type of resource (video, document, image, etc.)

        Returns:
            Response from resource creation or update
        """

        # Upload the file and get the URL
        resource_url = self.upload_file_to_storage(
            resource_path=resource_path,
            user_id=user_id,
            resource_type=resource_type,
            table_id=table_id,
            project_id=project_id
        )

        # Create new resource record
        return self.client.table("resources")\
            .insert({
                "table_id": table_id,
                "language": language,
                "resource_type": resource_type,
                "resource_index": resource_index,
                "resource_url": resource_url,
                "created_by": user_id
            }).execute().data[0]

    def delete_file_from_storage(
        self,
        file_path: str
    ) -> bool:
        """
        Delete a file from Supabase Storage.

        Args:
            file_path: Path to the file in storage (e.g., "project_id/table_id/file_name")

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.client.storage.from_(
                self.bucket).remove([file_path])
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
            return False

    def get_files_list(
        self,
        folder_path: str = "",
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "name",
        sort_order: str = "desc"
    ) -> List[Dict]:
        """
        Get list of files in a specific folder path.

        Args:
            folder_path: Path to the folder (e.g., "project_id/table_id")
            limit: Maximum number of files to return
            offset: Number of files to skip
            sort_by: Column to sort by ("name", "created_at", "updated_at")
            sort_order: Sort order ("asc" or "desc")

        Returns:
            List of file objects with metadata and URLs
        """
        try:
            # List files in the specified path with sorting options
            response = self.client.storage.from_(self.bucket).list(
                folder_path,
                {
                    "limit": limit,
                    "offset": offset,
                    "sortBy": {"column": sort_by, "order": sort_order}
                }
            )
            print(f"Files in {folder_path}: {response}")

            files_with_urls = []
            for file_obj in response:
                # Get public URL for each file
                file_path = f"{folder_path}/{file_obj['name']}" if folder_path else file_obj['name']
                public_url = self.client.storage.from_(
                    self.bucket).get_public_url(file_path)

                files_with_urls.append({
                    "name": file_obj['name'],
                    "id": file_obj.get('id'),
                    "size": file_obj.get('metadata', {}).get('size'),
                    "mime_type": file_obj.get('metadata', {}).get('mimetype'),
                    "created_at": file_obj.get('created_at'),
                    "updated_at": file_obj.get('updated_at'),
                    "public_url": public_url,
                    "file_path": file_path
                })

            return files_with_urls
        except Exception as e:
            print(f"Error listing files in {folder_path}: {str(e)}")
            return []

    def upload_file_bytes_to_storage(
        self,
        file_content: bytes,
        file_name: str,
        folder_path: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload file content (bytes) to Supabase Storage.

        Args:
            file_content: File content as bytes
            file_name: Name of the file
            folder_path: Folder path where to store the file
            content_type: MIME type of the file

        Returns:
            Public URL of the uploaded file
        """
        # Sanitize the file name
        file_name = sanitize_key(file_name)

        # Construct full upload path
        upload_path = f"{folder_path}/{file_name}" if folder_path else file_name

        try:
            # Try to upload the file
            self.client.storage.from_(self.bucket).upload(
                upload_path,
                file_content,
                file_options={"content-type": content_type}
            )
        except StorageException as e:
            if "already exists" in str(e).lower():
                # Update existing file
                self.client.storage.from_(self.bucket).update(
                    upload_path,
                    file_content,
                    file_options={"content-type": content_type}
                )
            else:
                raise e

        # Get public URL
        public_url = self.client.storage.from_(
            self.bucket).get_public_url(upload_path)
        return public_url

    async def upload_file_and_create_resource(
        self,
        file_content: bytes,
        file_name: str,
        project_id: str,
        table_id: str,
        user_id: str,
        resource_type: str = "file",
        resource_index: Optional[int] = None,
        content_type: str = "application/octet-stream",
        language: str = "english"
    ) -> Dict:
        """
        Upload file to storage and create a resource record.

        Args:
            file_content: File content as bytes
            file_name: Name of the file
            project_id: Project ID
            table_id: Table ID
            user_id: User ID who uploaded the file
            resource_type: Type of resource (default: "file")
            resource_index: Optional index for ordering
            content_type: MIME type of the file
            language: Language of the resource

        Returns:
            Dict containing resource record and file info
        """
        # Upload file to storage
        folder_path = f"{project_id}/{table_id}"
        public_url = self.upload_file_bytes_to_storage(
            file_content=file_content,
            file_name=file_name,
            folder_path=folder_path,
            content_type=content_type
        )

        resource_data = {
            "table_id": table_id,
            "resource_type": resource_type,
            "resource_url": public_url,
            "resource_name": file_name,
            "language": language,
            "created_by": user_id
        }

        if resource_index is not None:
            resource_data["resource_index"] = resource_index

        new_resource = await self.create(
            table="resources",
            data=resource_data
        )

        return {
            "resource": new_resource,
            "action": "created",
            "public_url": public_url,
            "file_info": {
                "file_name": file_name,
                "file_size": len(file_content),
                "content_type": content_type,
                "folder_path": folder_path
            }
        }

    async def delete_file_and_resource(
        self,
        project_id: str,
        table_id: str,
        file_name: str,
        resource_type: str = "file"
    ) -> Dict:
        """
        Delete file from storage and corresponding resource record.

        Args:
            project_id: Project ID
            table_id: Table ID
            file_name: Name of the file to delete
            resource_type: Type of resource to match

        Returns:
            Dict containing deletion results
        """
        file_path = f"{project_id}/{table_id}/{file_name}"

        # Delete file from storage
        file_deleted = self.delete_file_from_storage(file_path)

        # Find and delete corresponding resource record
        resource_deleted = False
        deleted_resource = None

        try:
            # Find the resource record
            existing_resource = await self.get(
                table="resources",
                filters={
                    "table_id": table_id,
                    "resource_name": file_name,
                    "resource_type": resource_type
                }
            )

            if existing_resource:
                # Delete the resource record
                await self.delete(
                    table="resources",
                    filters={"resource_id": existing_resource["resource_id"]}
                )
                resource_deleted = True
                deleted_resource = existing_resource

        except Exception as e:
            print(f"Error deleting resource record: {str(e)}")

        return {
            "file_deleted": file_deleted,
            "resource_deleted": resource_deleted,
            "deleted_resource": deleted_resource,
            "file_path": file_path
        }
