import unittest
from unittest.mock import patch, MagicMock, ANY
from ignition.service.infrastructure import InfrastructureNotFoundError, InvalidInfrastructureTemplateError
from ignition.model.infrastructure import CreateInfrastructureResponse, DeleteInfrastructureResponse, InfrastructureTask, FindInfrastructureResponse
from osvimdriver.service.infrastructure import InfrastructureDriver
from osvimdriver.service.tosca import ToscaValidationError
from osvimdriver.tosca.discover import DiscoveryResult, NotDiscoveredError
from tests.unit.testutils.constants import TOSCA_TEMPLATES_PATH, TOSCA_HELLO_WORLD_FILE


class TestInfrastructureDriver(unittest.TestCase):

    def setUp(self):
        self.mock_heat_input_utils = MagicMock()
        self.mock_heat_input_utils.filter_used_properties.return_value = {'propA': 'valueA'}
        self.mock_heat_driver = MagicMock()
        self.mock_os_location = MagicMock(heat_driver=self.mock_heat_driver)
        self.mock_os_location.get_heat_input_util.return_value = self.mock_heat_input_utils
        self.mock_location_translator = MagicMock()
        self.mock_location_translator.from_deployment_location.return_value = self.mock_os_location
        self.mock_heat_translator = MagicMock()
        self.mock_heat_translator.generate_heat_template.return_value = '''
                                                                        parameters:
                                                                          propA:
                                                                            type: string
                                                                        '''
        self.mock_tosca_discover_service = MagicMock()

    def test_create_infrastructure(self):
        self.mock_heat_driver.create_stack.return_value = '1'
        deployment_location = {'name': 'mock_location'}
        template = 'tosca_template'
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        result = driver.create_infrastructure(template, {'propA': 'valueA', 'propB': 'valueB'}, deployment_location)
        self.assertIsInstance(result, CreateInfrastructureResponse)
        self.assertEqual(result.infrastructure_id, '1')
        self.assertEqual(result.request_id, '1')
        self.mock_heat_translator.generate_heat_template.assert_called_once_with(template)
        self.mock_location_translator.from_deployment_location.assert_called_once_with(deployment_location)
        self.mock_heat_driver.create_stack.assert_called_once_with(ANY, self.mock_heat_translator.generate_heat_template.return_value, {'propA': 'valueA'})

    def test_create_infrastructure_with_invalid_template_throws_error(self):
        deployment_location = {'name': 'mock_location'}
        template = 'tosca_template'
        self.mock_heat_translator.generate_heat_template.side_effect = ToscaValidationError('Validation error')
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        with self.assertRaises(InvalidInfrastructureTemplateError) as context:
            driver.create_infrastructure(template, {'propA': 'valueA', 'propB': 'valueB'}, deployment_location)
        self.assertEqual(str(context.exception), 'Validation error')

    def test_delete_infrastructure(self):
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        result = driver.delete_infrastructure('1', deployment_location)
        self.assertIsInstance(result, DeleteInfrastructureResponse)
        self.assertEqual(result.infrastructure_id, '1')
        self.assertEqual(result.request_id, '1')
        self.mock_location_translator.from_deployment_location.assert_called_once_with(deployment_location)
        self.mock_heat_driver.delete_stack.assert_called_once_with('1')

    def test_get_infrastructure_tasks_requests_stack(self):
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.mock_location_translator.from_deployment_location.assert_called_once_with(deployment_location)
        self.mock_heat_driver.get_stack.assert_called_once_with('1')

    def test_get_infrastructure_task_create_in_progress(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'CREATE_IN_PROGRESS'
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'IN_PROGRESS')
        self.assertEqual(infrastructure_task.failure_details, None)
        self.assertEqual(infrastructure_task.outputs, None)

    def test_get_infrastructure_task_create_complete(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'CREATE_COMPLETE',
            'outputs': [
                {'output_key': 'outputA', 'output_value': 'valueA'},
                {'output_key': 'outputB', 'output_value': 'valueB'}
            ]
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'COMPLETE')
        self.assertEqual(infrastructure_task.failure_details, None)
        self.assertEqual(infrastructure_task.outputs, {'outputA': 'valueA', 'outputB': 'valueB'})

    def test_get_infrastructure_task_create_complete_no_outputs(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'CREATE_COMPLETE',
            'outputs': []
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'COMPLETE')
        self.assertEqual(infrastructure_task.failure_details, None)
        self.assertEqual(infrastructure_task.outputs, None)

    def test_get_infrastructure_task_create_complete_no_outputs_key(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'CREATE_COMPLETE'
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'COMPLETE')
        self.assertEqual(infrastructure_task.failure_details, None)
        self.assertEqual(infrastructure_task.outputs, None)

    def test_get_infrastructure_task_create_failed(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'CREATE_FAILED',
            'stack_status_reason': 'For the test'
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'FAILED')
        self.assertEqual(infrastructure_task.failure_details.failure_code, 'INFRASTRUCTURE_ERROR')
        self.assertEqual(infrastructure_task.failure_details.description, 'For the test')
        self.assertEqual(infrastructure_task.outputs, None)

    def test_get_infrastructure_task_create_failed_with_no_reason(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'CREATE_FAILED'
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'FAILED')
        self.assertEqual(infrastructure_task.failure_details.failure_code, 'INFRASTRUCTURE_ERROR')
        self.assertEqual(infrastructure_task.failure_details.description, None)
        self.assertEqual(infrastructure_task.outputs, None)

    def test_get_infrastructure_task_delete_in_progress(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'DELETE_IN_PROGRESS'
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'IN_PROGRESS')
        self.assertEqual(infrastructure_task.failure_details, None)
        self.assertEqual(infrastructure_task.outputs, None)

    def test_get_infrastructure_task_delete_complete(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'DELETE_COMPLETE'
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'COMPLETE')
        self.assertEqual(infrastructure_task.failure_details, None)
        self.assertEqual(infrastructure_task.outputs, None)

    def test_get_infrastructure_task_delete_failed(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'DELETE_FAILED',
            'stack_status_reason': 'For the test'
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'FAILED')
        self.assertEqual(infrastructure_task.failure_details.failure_code, 'INFRASTRUCTURE_ERROR')
        self.assertEqual(infrastructure_task.failure_details.description, 'For the test')
        self.assertEqual(infrastructure_task.outputs, None)

    def test_get_infrastructure_task_delete_failed_with_no_reason(self):
        self.mock_heat_driver.get_stack.return_value = {
            'id': '1',
            'stack_status': 'DELETE_FAILED'
        }
        deployment_location = {'name': 'mock_location'}
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        infrastructure_task = driver.get_infrastructure_task('1', '1', deployment_location)
        self.assertIsInstance(infrastructure_task, InfrastructureTask)
        self.assertEqual(infrastructure_task.infrastructure_id, '1')
        self.assertEqual(infrastructure_task.request_id, '1')
        self.assertEqual(infrastructure_task.status, 'FAILED')
        self.assertEqual(infrastructure_task.failure_details.failure_code, 'INFRASTRUCTURE_ERROR')
        self.assertEqual(infrastructure_task.failure_details.description, None)
        self.assertEqual(infrastructure_task.outputs, None)

    def test_find_infrastructure(self):
        self.mock_tosca_discover_service.discover.return_value = DiscoveryResult('1', {'test': '1'})
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        deployment_location = {'name': 'mock_location'}
        template = 'tosca_template'
        result = driver.find_infrastructure(template, 'test', deployment_location)
        self.assertIsInstance(result, FindInfrastructureResponse)
        self.assertEqual(result.infrastructure_id, '1')
        self.assertEqual(result.outputs, {'test': '1'})
        self.mock_location_translator.from_deployment_location.assert_called_once_with(deployment_location)
        self.mock_tosca_discover_service.discover.assert_called_once_with(template, self.mock_location_translator.from_deployment_location.return_value, {'instance_name': 'test'})

    def test_find_infrastructure_returns_error_when_not_found(self):
        self.mock_tosca_discover_service.discover.side_effect = NotDiscoveredError('Not found')
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        deployment_location = {'name': 'mock_location'}
        template = 'tosca_template'
        with self.assertRaises(InfrastructureNotFoundError) as context:
            driver.find_infrastructure(template, 'test', deployment_location)
        self.assertEqual(str(context.exception), 'Not found')

    def test_find_infrastructure_with_invalid_template_throws_error(self):
        self.mock_tosca_discover_service.discover.side_effect = ToscaValidationError('Validation error')
        driver = InfrastructureDriver(self.mock_location_translator, heat_translator_service=self.mock_heat_translator, tosca_discovery_service=self.mock_tosca_discover_service)
        deployment_location = {'name': 'mock_location'}
        template = 'tosca_template'
        with self.assertRaises(InvalidInfrastructureTemplateError) as context:
            driver.find_infrastructure(template, 'test', deployment_location)
        self.assertEqual(str(context.exception), 'Validation error')