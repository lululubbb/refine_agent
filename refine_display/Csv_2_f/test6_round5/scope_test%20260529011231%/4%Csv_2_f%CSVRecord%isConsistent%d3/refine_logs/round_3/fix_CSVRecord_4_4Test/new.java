package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_4_4Test {

    @Test
    public void testisConsistent_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true when mapping is null");
    }

    @Test
    public void testisConsistent_mappingSizeEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true when mapping size equals values length");
    }

    @Test
    public void testisConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected isConsistent to return false when mapping size does not equal values length");
    }

    @Test
    public void testisConsistent_emptyValuesAndNullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true for empty values and null mapping");
    }

    @Test
    public void testisConsistent_emptyValuesAndEmptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true for empty values and empty mapping");
    }

    @Test
    public void testisConsistent_singleValueWithNullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true for single value with null mapping");
    }

    @Test
    public void testisConsistent_singleValueWithEmptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected isConsistent to return false for single value with empty mapping");
    }

    @Test
    public void testisConsistent_boundaryValues() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected isConsistent to return false for single value with mapping size not matching values length");
        
        mapping.put("key2", 1);
        record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true when mapping size equals values length for two values");
        
        mapping.remove("key2");
        record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected isConsistent to return false when mapping size less than values length");
    }
}