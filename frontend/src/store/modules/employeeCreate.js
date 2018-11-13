import { getField, updateField } from 'vuex-map-fields'
import Service from '@/api/HttpCommon'

const state = {
  employee: {},
  engagement: {},
  address: [],
  association: [],
  role: [],
  itSystem: [],
  manager: [],
  backendValidationError: null
}

const actions = {
  CREATE_EMPLOYEE ({commit, state}) {
    let create = [].concat(state.engagement, state.address, state.association, state.role, state.itSystem, state.manager)

    create.forEach(e => {
      if (!e.validity) {
        e.validity = state.engagement.validity
      }
    })

    let newEmployee = {
      name: state.employee.name,
      cpr_no: state.employee.cpr_no,
      org: state.engagement.org_unit,
      details: create
    }

    return Service.post('/e/create', newEmployee)
      .then(response => {
        let employeeUuid = response.data
        if (Array.isArray(response.data)) {
          employeeUuid = response.data[0]
        }
        if (response.data.error) {
          return response.data
        }
        commit('log/newWorkLog', { type: 'EMPLOYEE_CREATE', value: employeeUuid }, { root: true })
        return employeeUuid
      })
      .catch(error => {
        commit('log/newError', { type: 'ERROR', value: error.response.data }, { root: true })
        return error.response.data
      })
  },

  resetFields ({ commit }) {
    commit('resetFields')
  }
}

const mutations = {
  updateField,

  resetFields (state) {
    state.employee = {}
    state.engagement = {}
    state.address = []
    state.association = []
    state.role = []
    state.itSystem = []
    state.manager = []
    state.backendValidationError = null
  }
}

const getters = {
  getField
}

export default {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}