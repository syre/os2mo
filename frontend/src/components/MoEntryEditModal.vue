SPDX-FileCopyrightText: 2018-2020 Magenta ApS
SPDX-License-Identifier: MPL-2.0
<template>
  <div v-if="hasEntryComponent">
    <button
      class="btn btn-outline-primary"
      v-b-modal="nameId"
      :disabled="disabled"
    >
      <icon name="edit" />
    </button>

    <b-modal
      :id="nameId"
      size="lg"
      hide-footer
      :title="$t('common.edit')"
      :ref="nameId"
      lazy
    >
    <form @submit.stop.prevent="edit">
      <component
        :is="entryComponent"
        v-model="entry"
        :disable-org-unit-picker="disableOrgUnitPicker"
        :hide-org-picker="hideOrgPicker"
        :hide-employee-picker="hideEmployeePicker"
        :is-edit="true"
      />

      <div class="alert alert-danger" v-if="backendValidationMessage">
        {{backendValidationMessage}}
      </div>

      <div class="float-right">
        <button-submit :is-loading="isLoading"/>
      </div>
    </form>
    </b-modal>
  </div>
</template>

<script>
/**
 * A entry edit modal component.
 */

import Employee from '@/api/Employee'
import OrganisationUnit from '@/api/OrganisationUnit'
import ButtonSubmit from './ButtonSubmit'
import ValidateForm from '@/mixins/ValidateForm'
import ModalBase from '@/mixins/ModalBase'
import bModalDirective from 'bootstrap-vue/es/directives/modal/modal'

export default {
  mixins: [ValidateForm, ModalBase],

  components: {
    ButtonSubmit
  },
  directives: {
    'b-modal': bModalDirective
  },

  props: {
    /**
     * Defines a uuid.
     */
    uuid: String,

    /**
     * Defines a label.
     */
    label: String,

    /**
     * Defines the content.
     */
    content: Object,

    /**
     * Defines the contentType.
     */
    contentType: String,

    /**
     * Defines the entryComponent.
     */
    entryComponent: Object,

    /**
     * Whether the button is disabled
     */
    disabled: { type: Boolean, default: false },

    /**
     * Defines a required type - employee or organisation unit.
     */
    type: {
      type: String,
      required: true,
      validator (value) {
        if (value === 'EMPLOYEE' || value === 'ORG_UNIT') return true
        console.warn('Action must be either EMPLOYEE or ORG_UNIT')
        return false
      }
    }
  },

  data () {
    return {
      /**
       * The entry, isLoading, backendValidationMessage component value.
       * Used to detect changes and restore the value.
       */
      entry: {},
      isLoading: false,
      backendValidationMessage: null
    }
  },

  computed: {
    /**
     * Get name `moEdit`.
     */
    nameId () {
      return 'moEdit' + this._uid
    },

    /**
     * Get disableOrgUnitPicker type.
     */
    disableOrgUnitPicker () {
      return this.type === 'ORG_UNIT'
    },

    /**
     * Get hideOrgPicker type.
     */
    hideOrgPicker () {
      return this.type === 'ORG_UNIT'
    },

    /**
     * Get hideEmployeePicker type.
     */
    hideEmployeePicker () {
      return this.type === 'EMPLOYEE'
    },

    /**
     * If it has a entry component.
     */
    hasEntryComponent () {
      return this.entryComponent !== undefined
    }
  },

  watch: {
    /**
     * Whenever content change, update newVal.
     */
    content: {
      handler (newVal) {
        this.handleContent(newVal)
      },
      deep: true
    }
  },

  mounted () {
    /**
     * Whenever content change preselected value.
     */
    this.handleContent(this.content)

    this.backendValidationMessage = null

    this.$root.$on('bv::modal::shown', data => {
      if (this.content) {
        this.handleContent(this.content)
      }
    })
  },

  beforeDestroy () {
    /**
     * Called right before a instance is destroyed.
     */
    this.$root.$off(['bv::modal::shown'])
  },

  methods: {
    /**
     * Handle the entry content.
     */
    handleContent (content) {
      this.entry = JSON.parse(JSON.stringify(content))
    },

    /**
     * Edit a employee or organisation entry.
     */
    edit () {
      if (!this.formValid) {
        this.$validator.validateAll()
        return
      }

      this.isLoading = true

      let data = {
        type: this.contentType,
        uuid: this.entry.uuid,
        data: this.entry
      }

      switch (this.type) {
        case 'EMPLOYEE':
          data.person = { uuid: this.uuid }
          this.editEmployee(data)
          break
        case 'ORG_UNIT':
          data.org_unit = { uuid: this.uuid }
          this.editOrganisationUnit(data)
          break
      }
    },

    /**
     * Edit a employee and check if the data fields are valid.
     * Then throw a error if not.
     */
    editEmployee (data) {
      return Employee.edit(data).then(this.handle.bind(this))
    },

    /**
     * Edit a organisation and check if the data fields are valid.
     * Then throw a error if not.
     */
    editOrganisationUnit (data) {
      return OrganisationUnit.edit(data).then(this.handle.bind(this))
    },

    handle (response) {
      this.isLoading = false
      if (response.error) {
        this.backendValidationMessage =
            this.$t('alerts.error.' + response.error_key, response)

        if (!this.backendValidationMessage) {
          this.backendValidationMessage = this.$t('alerts.fallback', response)
        }
      } else {
        this.$refs[this.nameId].hide()
        this.$emit('submit')

        if (this.type === 'EMPLOYEE') {
          this.$store.commit('log/newWorkLog',
            {
              type: 'EMPLOYEE_EDIT',
              contentType: this.contentType,
              value: this.uuid
            },
            { root: true })
        }

        if (this.type === 'ORG_UNIT') {
          this.$store.commit('log/newWorkLog',
            {
              type: 'ORGANISATION_EDIT',
              contentType: this.contentType,
              value: this.uuid
            },
            { root: true })
        }
      }
    }
  }
}
</script>
