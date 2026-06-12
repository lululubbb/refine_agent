package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_4_1Test {

    @Test
    public void testisConsistent_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertEquals(true, record.isConsistent(), "Expected isConsistent to return true when mapping is null.");
    }

    @Test
    public void testisConsistent_mappingSizeMatchesValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertEquals(true, record.isConsistent(), "Expected isConsistent to return true when mapping size matches values length.");
    }

    @Test
    public void testisConsistent_mappingSizeDoesNotMatchValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertEquals(false, record.isConsistent(), "Expected isConsistent to return false when mapping size does not match values length.");
    }

    @Test
    public void testisConsistent_emptyMappingAndValues() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, Collections.emptyMap(), null, 1);
        Assertions.assertEquals(true, record.isConsistent(), "Expected isConsistent to return true for empty mapping and values.");
    }

    @Test
    public void testisConsistent_emptyValuesWithNullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, null, null, 1);
        Assertions.assertEquals(true, record.isConsistent(), "Expected isConsistent to return true for empty values with null mapping.");
    }

    @Test
    public void testisConsistent_singleValueWithMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertEquals(true, record.isConsistent(), "Expected isConsistent to return true for single value with correct mapping.");
    }

    @Test
    public void testisConsistent_singleValueWithIncorrectMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 1); // Incorrect index
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertEquals(false, record.isConsistent(), "Expected isConsistent to return false for single value with incorrect mapping.");
    }
    
    public static class CSVRecord implements Serializable, Iterable<String> {
        private static final long serialVersionUID = 1L;
        private final String[] values;
        private final Map<String, Integer> mapping;

        CSVRecord(final String[] values, final Map<String, Integer> mapping, final String comment, final long recordNumber) {
            this.values = values;
            this.mapping = mapping;
        }

        public boolean isConsistent() {
            if (mapping == null) {
                return true;
            }
            for (Integer index : mapping.values()) {
                if (index < 0 || index >= values.length) {
                    return false;
                }
            }
            return mapping.size() == values.length;
        }

        @Override
        public Iterator<String> iterator() {
            return Arrays.asList(values).iterator();
        }
    }
}