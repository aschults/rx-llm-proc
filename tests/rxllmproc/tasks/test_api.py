# pyright: reportPrivateUsage=false
"""Test the Google Tasks API wrapper."""

import unittest
import dataclasses
from typing import Any, cast
from unittest import mock

from google.oauth2 import credentials

from rxllmproc.tasks import types as tasks_types
from rxllmproc.tasks import api as tasks_wrapper, _tasks_interface
import datetime

import test_support

# Date to be used for test cases.
_REF_DATE = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)


def _build_task_result(*task_ids: str, page_token: str | None = None) -> Any:
    """Create a task object as returned from the API."""
    tasks = [
        {
            'id': task_id,
            'title': 'blah',
            'updated': '2024-01-01T00:00:00Z',
            'selfLink': None,
            'status': 'needsAction',
        }
        for task_id in task_ids
    ]
    result = {
        'kind': 'kind',
        'etag': 'blah',
        'items': tasks,
    }
    if page_token:
        result['nextPageToken'] = page_token

    return result


def _build_tasklists_result(*list_ids: str) -> Any:
    """Create a tasklist object, as returned from the API."""
    tasklists = [
        tasks_types.TaskList(id=list_id, title='blah') for list_id in list_ids
    ]
    return dataclasses.asdict(
        _tasks_interface.TaskListResponse('kind', 'blah', tasklists)
    )


class TestWrapper(unittest.TestCase):
    """Test the wrapper class."""

    def setUp(self) -> None:
        """Provide mock creds and service, and a wrapper instance."""
        self.creds = mock.Mock(spec=credentials.Credentials)
        self.service = mock.Mock(spec=_tasks_interface.TasksServiceInterface)

        tasks_service_mock = self.service.tasks.return_value
        self.list_mock = tasks_service_mock.list
        self.list_execute_mock = self.list_mock.return_value.execute
        self.get_mock = tasks_service_mock.get
        self.get_execute_mock = self.get_mock.return_value.execute
        self.insert_mock = tasks_service_mock.insert
        self.insert_execute_mock = self.insert_mock.return_value.execute
        self.delete_mock = tasks_service_mock.delete
        self.delete_execute_mock = self.delete_mock.return_value.execute
        self.update_mock = tasks_service_mock.update
        self.update_execute_mock = self.update_mock.return_value.execute
        self.move_mock = tasks_service_mock.move
        self.move_execute_mock = self.move_mock.return_value.execute

        tasklists_service_mock = self.service.tasklists.return_value
        self.tasklists_list_mock = tasklists_service_mock.list
        self.tasklists_list_execute_mock = (
            self.tasklists_list_mock.return_value.execute
        )

        self.wrapper = tasks_wrapper.TasksWrap(self.creds, self.service)
        return super().setUp()

    def test_list_tasks(self):
        """Test listing tasks."""
        self.list_execute_mock.return_value = _build_task_result('taskid1')

        result = list(self.wrapper.generate_tasks('listid1'))
        self.assertEqual(
            [
                (
                    'listid1',
                    tasks_types.Task(
                        title='blah',
                        status='needsAction',
                        id='taskid1',
                        updated=_REF_DATE,
                    ),
                )
            ],
            result,
        )
        self.list_mock.assert_called_with(
            showCompleted=False,
            showDeleted=False,
            showHidden=False,
            tasklist='listid1',
            maxResults=100,
            pageToken=None,
        )

    def test_list_tasks_paging(self):
        """Test listing tasks from multiple, paged requests."""
        self.list_execute_mock.side_effect = [
            _build_task_result('taskid1', 'taskid2', page_token='tok'),
            _build_task_result('taskid3'),
        ]
        result = list(self.wrapper.generate_tasks('listid1'))

        self.maxDiff = None
        self.assertEqual(
            [
                (
                    'listid1',
                    tasks_types.Task(
                        title='blah',
                        status='needsAction',
                        id=f'taskid{i}',
                        updated=_REF_DATE,
                    ),
                )
                for i in (1, 2, 3)
            ],
            result,
        )
        self.list_mock.assert_has_calls(
            [
                mock.call(
                    showCompleted=False,
                    showDeleted=False,
                    showHidden=False,
                    tasklist='listid1',
                    maxResults=100,
                    pageToken=None,
                ),
                mock.call().execute(),
                mock.call(
                    showCompleted=False,
                    showDeleted=False,
                    showHidden=False,
                    tasklist='listid1',
                    maxResults=100,
                    pageToken='tok',
                ),
                mock.call().execute(),
            ]
        )
        self.assertEqual(2, self.list_execute_mock.call_count)

    def test_list_tasks_fields(self):
        """Test generating tasks for all lists if no ID is provided."""
        self.tasklists_list_execute_mock.return_value = _build_tasklists_result(
            'list1', 'list2'
        )

        self.list_execute_mock.side_effect = [
            _build_task_result('task1'),
            _build_task_result('task2'),
        ]

        result = list(self.wrapper.generate_tasks())
        self.assertEqual(2, len(result))
        self.assertEqual('task1', result[0][1].id)
        self.assertEqual('task2', result[1][1].id)

        self.list_mock.assert_has_calls(
            [
                mock.call(
                    showCompleted=False,
                    showDeleted=False,
                    showHidden=False,
                    tasklist='list1',
                    maxResults=100,
                    pageToken=None,
                ),
                mock.call().execute(),
                mock.call(
                    showCompleted=False,
                    showDeleted=False,
                    showHidden=False,
                    tasklist='list2',
                    maxResults=100,
                    pageToken=None,
                ),
                mock.call().execute(),
            ]
        )
        self.assertEqual(2, self.list_execute_mock.call_count)

    def test_generate_tasks_all_lists(self):
        """Check that Task fields are converted properly."""
        self.list_execute_mock.return_value = {
            'kind': 'kind',
            'etag': 'blah',
            'items': [
                {
                    'id': 'taskid1',
                    'title': 'blah',
                    'updated': '2024-01-01T00:00:41Z',
                    'selfLink': None,
                    'position': '99',
                    'status': 'needsAction',
                    'links': [],
                    'notes': None,
                    'parent': None,
                    'completed': '2024-01-01T00:00:42Z',
                    'deleted': None,
                    'hidden': None,
                    'due': '2024-01-01T00:00:43Z',
                }
            ],
            'nextPageToken': None,
        }
        result = list(self.wrapper.generate_tasks('listid1'))
        self.maxDiff = None
        self.assertEqual(
            41, test_support.fail_none(result[0][1].updated).second
        )
        self.assertEqual(
            42, test_support.fail_none(result[0][1].completed).second
        )
        self.assertEqual(43, test_support.fail_none(result[0][1].due).second)
        self.assertEqual(99, test_support.fail_none(result[0][1].position))

    def test_list_tasklists(self):
        """Test listing task lists."""
        self.tasklists_list_execute_mock.return_value = _build_tasklists_result(
            'id1'
        )
        result = list(self.wrapper.generate_lists())
        self.assertEqual([tasks_types.TaskList(id='id1', title='blah')], result)
        self.tasklists_list_mock.assert_called_with(maxResults=100)

    def test_list_tasklists_fields(self):
        """Ensure task list fields are converted correctly."""
        self.tasklists_list_execute_mock.return_value = {
            'kind': 'kind',
            'etag': 'blah',
            'items': [
                {
                    'kind': 'tasks#taskList',
                    'title': 'blah',
                    'id': 'id1',
                    'etag': None,
                    'updated': '2024-01-01T00:00:41Z',
                    'selfLink': None,
                }
            ],
            'nextPageToken': None,
        }
        result = list(self.wrapper.generate_lists())
        self.assertEqual(41, test_support.fail_none(result[0].updated).second)

    def test_add_task(self):
        """Test adding a task."""
        self.insert_execute_mock.return_value = {
            'id': 'taskid1',
            'title': 'blah',
            'updated': '2024-01-01T00:00:41Z',
            'selfLink': None,
            'position': '99',
            'status': 'needsAction',
            'links': [],
            'notes': None,
            'parent': None,
            'completed': '2024-01-01T00:00:42Z',
            'deleted': None,
            'hidden': None,
            'due': '2024-01-01T00:00:43Z',
        }

        tasklist = tasks_types.TaskList(title='testlist', id='listid')
        task = tasks_types.Task(
            status='needsAction',
            updated=_REF_DATE,
            position=22,
            due=_REF_DATE,
            completed=_REF_DATE,
            title='blah',
        )
        self.wrapper.add_task(task, tasklist)

        self.assertEqual(task.id, 'taskid1')
        self.maxDiff = None
        self.insert_mock.assert_called_with(
            body={
                'status': 'needsAction',
                'title': 'blah',
                'kind': 'tasks#task',
                'position': '22',
                'updated': '2024-01-01T00:00:00+00:00',
                'id': None,
                'etag': None,
                'selfLink': None,
                'links': [],
                'notes': None,
                'parent': None,
                'completed': '2024-01-01T00:00:00+00:00',
                'deleted': None,
                'hidden': None,
                'due': '2024-01-01T00:00:00+00:00',
            },
            tasklist='listid',
        )

    def test_get_task(self):
        """Test getting a single task."""
        self.get_execute_mock.return_value = {
            'id': 'taskid1',
            'title': 'blah',
            'updated': '2024-01-01T00:00:00Z',
            'status': 'needsAction',
        }
        task = self.wrapper.get_task('listid1', 'taskid1')
        self.assertEqual('taskid1', task.id)
        self.get_mock.assert_called_with(tasklist='listid1', task='taskid1')

    def test_delete_task(self):
        """Test deleting a task."""
        self.wrapper.delete_task('listid1', 'taskid1')
        self.delete_mock.assert_called_with(tasklist='listid1', task='taskid1')
        self.delete_execute_mock.assert_called_once()

    def test_update_task(self):
        """Test updating a task."""
        task = tasks_types.Task(
            id='taskid1', title='new title', status='needsAction'
        )
        self.update_execute_mock.return_value = {
            'id': 'taskid1',
            'title': 'new title',
            'updated': '2024-01-01T00:00:01Z',
            'status': 'needsAction',
            'etag': 'new_etag',
        }
        self.wrapper.update_task(task, 'listid1')
        self.assertEqual('new_etag', task.etag)
        self.assertEqual(1, test_support.fail_none(task.updated).second)
        self.update_mock.assert_called_with(
            tasklist='listid1', task='taskid1', body=mock.ANY
        )

    def test_move_task(self):
        """Test moving a task."""
        self.move_execute_mock.return_value = {
            'id': 'taskid1',
            'title': 'blah',
            'updated': '2024-01-01T00:00:00Z',
            'status': 'needsAction',
        }
        moved_task = self.wrapper.move_task('taskid1', 'listid1', 'listid2')
        self.assertEqual('taskid1', moved_task.id)
        self.move_mock.assert_called_with(
            tasklist='listid1', task='taskid1', destinationTasklist='listid2'
        )

    def test_upsert_task_create_no_id(self):
        """Test upsert creates a new task when no ID is provided and title doesn't match."""
        self.list_execute_mock.return_value = _build_task_result(
            'existing_task'
        )
        self.insert_execute_mock.return_value = {
            'id': 'new_task_id',
            'title': 'new task',
            'updated': '2024-01-01T00:00:00Z',
            'status': 'needsAction',
        }

        new_task = tasks_types.Task(title='new task', status='needsAction')
        self.wrapper.upsert_task(new_task, 'listid1')

        self.insert_mock.assert_called_once()
        self.assertEqual('new_task_id', new_task.id)

    def test_upsert_task_create_with_id_not_found(self):
        """Test upsert creates a new task when ID is provided but not found."""
        self.get_mock.side_effect = tasks_wrapper.TaskNotFoundError("Not Found")
        self.list_execute_mock.return_value = (
            _build_task_result()
        )  # No matching title
        self.insert_execute_mock.return_value = {
            'id': 'new_task_id',
            'title': 'new task',
            'updated': '2024-01-01T00:00:00Z',
            'status': 'needsAction',
        }

        new_task = tasks_types.Task(
            id='non_existent_id', title='new task', status='needsAction'
        )
        with self.assertRaises(tasks_wrapper.TaskNotFoundError):
            self.wrapper.upsert_task(new_task, 'listid1')

        # upsert should just raise when a task ID is set but no longer found.
        self.insert_mock.assert_not_called()

    def test_upsert_task_update_by_id(self):
        """Test upsert updates an existing task found by ID."""
        existing_task_dict = {
            'id': 'taskid1',
            'title': 'old title',
            'status': 'needsAction',
            'updated': '2024-01-01T00:00:00Z',
        }
        self.get_execute_mock.return_value = existing_task_dict
        self.update_execute_mock.return_value = {
            'id': 'taskid1',
            'title': 'new title',
            'status': 'needsAction',
            'updated': '2024-01-01T00:00:01Z',
            'etag': 'new_etag',
        }

        updated_task = tasks_types.Task(
            id='taskid1', title='new title', status='needsAction'
        )
        self.wrapper.upsert_task(updated_task, 'listid1')

        self.assertEqual('new_etag', updated_task.etag)
        self.assertEqual(1, test_support.fail_none(updated_task.updated).second)
        self.update_mock.assert_called_once()
        self.insert_mock.assert_not_called()

    def test_upsert_task_no_update_if_same(self):
        """Test upsert does not update if task is identical."""
        existing_task_dict = {
            'id': 'taskid1',
            'title': 'same title',
            'status': 'needsAction',
            'updated': '2024-01-01T00:00:00Z',
        }
        self.get_execute_mock.return_value = existing_task_dict

        same_task = tasks_types.Task(
            id='taskid1', title='same title', status='needsAction'
        )
        self.wrapper.upsert_task(same_task, 'listid1')

        self.update_mock.assert_not_called()
        self.insert_mock.assert_not_called()


class TestManagedTasks(unittest.TestCase):
    """Test the ManagedTasks class."""

    def setUp(self) -> None:
        """Set up mocks."""
        self.tasks_wrapper_mock = mock.Mock(spec=tasks_wrapper.TasksWrap)
        self.managed_tasks = tasks_wrapper.ManagedTasks(self.tasks_wrapper_mock)

    def test_get_id_url(self):
        """Test extracting the ID URL from notes."""
        task = tasks_types.Task(
            status='needsAction',
            title='t',
            notes='\U0001f517http://example.com/id/1\nSome other note.',
        )
        self.assertEqual(
            'http://example.com/id/1', self.managed_tasks._get_id_url(task)
        )

    def test_get_id_url_no_notes(self):
        """Test _get_id_url with no notes."""
        task = tasks_types.Task(status='needsAction', title='t', notes=None)
        self.assertIsNone(self.managed_tasks._get_id_url(task))

    def test_get_id_url_no_id(self):
        """Test _get_id_url with notes but no ID."""
        task = tasks_types.Task(
            status='needsAction', title='t', notes='Some other note.'
        )
        self.assertIsNone(self.managed_tasks._get_id_url(task))

    def test_set_id_url_new(self):
        """Test setting an ID URL on a task with no notes."""
        task = tasks_types.Task(status='needsAction', title='t')
        self.managed_tasks._set_id_url(task, 'http://example.com/id/2')
        self.assertEqual('\U0001f517http://example.com/id/2', task.notes)

    def test_set_id_url_replace(self):
        """Test replacing an existing ID URL."""
        task = tasks_types.Task(
            status='needsAction',
            title='t',
            notes='\U0001f517http://example.com/id/1\nOther stuff.',
        )
        self.managed_tasks._set_id_url(task, 'http://example.com/id/2')
        self.assertEqual(
            '\U0001f517http://example.com/id/2\nOther stuff.', task.notes
        )

    def test_find_by_id_url(self):
        """Test finding a task by its ID URL."""
        task1 = tasks_types.Task(
            id='task1',
            status='needsAction',
            title='t1',
            notes='\U0001f517http://example.com/id/1',
        )
        task2 = tasks_types.Task(
            id='task2',
            status='needsAction',
            title='t2',
            notes='no id here',
            updated=_REF_DATE,
        )
        self.tasks_wrapper_mock.generate_tasks.return_value = iter(
            [('list1', task1), ('list1', task2)]
        )

        found_task = self.managed_tasks.find_by_id_url(
            'http://example.com/id/1'
        )

        self.assertIsNotNone(found_task)
        found_task = cast(tasks_types.ManagedTask, found_task)
        self.assertEqual('http://example.com/id/1', found_task.id_url)
        self.assertEqual('task1', found_task.id)
        self.assertEqual('list1', found_task.tasklist_id)
        self.tasks_wrapper_mock.generate_tasks.assert_called_with(None)

    def test_find_by_id_url_not_found(self):
        """Test find_by_id_url when no task matches."""
        task1 = tasks_types.Task(
            id='task1',
            status='needsAction',
            title='t1',
            notes='no id',
            updated=_REF_DATE,
        )
        self.tasks_wrapper_mock.generate_tasks.return_value = iter(
            [('list1', task1)]
        )

        found_task = self.managed_tasks.find_by_id_url(
            'http://example.com/id/nonexistent'
        )
        self.assertIsNone(found_task)

    def test_upsert_managed_task_create(self):
        """Test creating a new managed task."""
        with mock.patch.object(
            self.managed_tasks, 'find_by_id_url', return_value=None
        ) as find_mock:
            managed_task = tasks_types.ManagedTask(
                id_url='http://a.b/1',
                tasklist_id='list1',
                title='new',
                status='needsAction',
            )

            self.managed_tasks.upsert_managed_task(managed_task)

            find_mock.assert_called_with('http://a.b/1')
            self.tasks_wrapper_mock.upsert_task.assert_called_once()
            # Check that _set_id_url was called
            self.assertIn(
                '\U0001f517http://a.b/1',
                test_support.fail_none(managed_task.notes),
            )
            # Check that the task passed to upsert_task is the managed_task
            self.tasks_wrapper_mock.upsert_task.assert_called_with(
                managed_task, 'list1'
            )

    def test_upsert_managed_task_update(self):
        """Test updating an existing managed task in the same list."""
        existing_task = tasks_types.ManagedTask(
            id='t1',
            id_url='http://a.b/1',
            tasklist_id='list1',
            title='old',
            status='needsAction',
        )
        with mock.patch.object(
            self.managed_tasks, 'find_by_id_url', return_value=existing_task
        ) as find_mock:
            managed_task = tasks_types.ManagedTask(
                id_url='http://a.b/1',
                tasklist_id='list1',
                title='new',
                status='needsAction',
            )

            self.managed_tasks.upsert_managed_task(managed_task)

            find_mock.assert_called_with('http://a.b/1')
            self.tasks_wrapper_mock.move_task.assert_not_called()
            self.tasks_wrapper_mock.upsert_task.assert_called_with(
                existing_task, 'list1'
            )
            self.assertIn(
                '\U0001f517http://a.b/1',
                test_support.fail_none(managed_task.notes),
            )
            self.assertEqual(managed_task.notes, existing_task.notes)

    def test_upsert_managed_task_move(self):
        """Test moving an existing managed task to a new list."""
        existing_task = tasks_types.ManagedTask(
            id='t1',
            id_url='http://a.b/1',
            tasklist_id='list1',
            title='task',
            status='needsAction',
        )
        moved_task_from_api = tasks_types.Task(
            id='t1_moved', title='task', status='needsAction'
        )

        with mock.patch.object(
            self.managed_tasks, 'find_by_id_url', return_value=existing_task
        ) as find_mock:
            self.tasks_wrapper_mock.move_task.return_value = moved_task_from_api
            managed_task_to_upsert = tasks_types.ManagedTask(
                id_url='http://a.b/1',
                tasklist_id='list2',
                title='task',
                status='needsAction',
            )

            self.managed_tasks.upsert_managed_task(managed_task_to_upsert)

            find_mock.assert_called_with('http://a.b/1')
            self.tasks_wrapper_mock.move_task.assert_called_with(
                't1', 'list1', 'list2'
            )

            # No upsert as no other fields are modified.
            self.tasks_wrapper_mock.upsert_task.assert_not_called()

    def test_generate_managed_tasks(self):
        """Test generating all managed tasks."""
        task1 = tasks_types.Task(
            id='t1',
            status='needsAction',
            title='t1',
            notes='\U0001f517http://a.b/1',
        )
        task2 = tasks_types.Task(
            id='t2', status='needsAction', title='t2', notes='not managed'
        )
        task3 = tasks_types.Task(
            id='t3',
            status='needsAction',
            title='t3',
            notes='\U0001f517http://a.b/3',
        )
        self.tasks_wrapper_mock.generate_tasks.return_value = iter(
            [('list1', task1), ('list1', task2), ('list1', task3)]
        )

        result = list(self.managed_tasks.generate_managed_tasks('list1'))

        self.assertEqual(2, len(result))
        self.assertEqual('http://a.b/1', result[0].id_url)
        self.assertEqual('list1', result[0].tasklist_id)
        self.assertEqual('http://a.b/3', result[1].id_url)
        self.assertEqual('list1', result[1].tasklist_id)
        self.tasks_wrapper_mock.generate_tasks.assert_called_with('list1')

    def test_upsert_managed_task_create_default_list(self):
        """Test creating a managed task using default tasklist ID."""
        with mock.patch.object(
            self.managed_tasks, 'find_by_id_url', return_value=None
        ) as find_mock:
            managed_task = tasks_types.ManagedTask(
                id_url='http://a.b/1',
                tasklist_id=None,
                title='new',
                status='needsAction',
            )

            self.managed_tasks.upsert_managed_task(
                managed_task, default_tasklist_id='default_list'
            )

            find_mock.assert_called_with('http://a.b/1')
            self.assertEqual('default_list', managed_task.tasklist_id)
            self.tasks_wrapper_mock.upsert_task.assert_called_with(
                managed_task, 'default_list'
            )

    def test_upsert_managed_task_update_no_change_with_id(self):
        """Test updating a managed task with no effective changes, ignoring ID."""
        existing_task = tasks_types.ManagedTask(
            id='t1',
            id_url='http://a.b/1',
            tasklist_id='list1',
            title='title',
            status='needsAction',
        )
        with mock.patch.object(
            self.managed_tasks, 'find_by_id_url', return_value=existing_task
        ) as find_mock:
            # managed_task has 'id' set, which should be ignored.
            # title and status match existing.
            managed_task = tasks_types.ManagedTask(
                id='different_id',
                id_url='http://a.b/1',
                tasklist_id='list1',
                title='title',
                status='needsAction',
            )

            self.managed_tasks.upsert_managed_task(managed_task)

            find_mock.assert_called_with('http://a.b/1')
            self.tasks_wrapper_mock.upsert_task.assert_not_called()

    def test_upsert_managed_task_update_same_list_no_change(self):
        """Test updating a managed task with same list and no changes."""
        existing_task = tasks_types.ManagedTask(
            id='t1',
            id_url='http://a.b/1',
            tasklist_id='list1',
            title='title',
            status='needsAction',
        )
        with mock.patch.object(
            self.managed_tasks, 'find_by_id_url', return_value=existing_task
        ) as find_mock:
            managed_task = tasks_types.ManagedTask(
                id_url='http://a.b/1',
                tasklist_id='list1',
                title='title',
                status='needsAction',
            )

            self.managed_tasks.upsert_managed_task(managed_task)

            find_mock.assert_called_with('http://a.b/1')
            self.tasks_wrapper_mock.move_task.assert_not_called()
            self.tasks_wrapper_mock.upsert_task.assert_not_called()
