package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_4_2Test {

    @Test
    public void testIsConsistent_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true when mapping is null");
    }

    @Test
    public void testIsConsistent_mappingSizeEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true when mapping size equals values length");
    }

    @Test
    public void testIsConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1); // Adding an extra mapping to trigger inconsistency
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected isConsistent to return false when mapping size does not equal values length");
    }

    @Test
    public void testIsConsistent_emptyValuesAndMapping() throws Exception {
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(new String[]{}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true with empty values and mapping");
    }

    @Test
    public void testIsConsistent_emptyValuesAndNullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true when both values and mapping are empty");
    }

    @Test
    public void testIsConsistent_singleValueWithNullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true when single value and mapping is null");
    }

    @Test
    public void testIsConsistent_singleValueWithMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to return true when single value with correct mapping");
    }

    @Test
    public void testIsConsistent_multipleValuesWithIncorrectMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        mapping.put("column3", 2); // Extra mapping
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected isConsistent to return false when mapping size exceeds values length");
    }
}