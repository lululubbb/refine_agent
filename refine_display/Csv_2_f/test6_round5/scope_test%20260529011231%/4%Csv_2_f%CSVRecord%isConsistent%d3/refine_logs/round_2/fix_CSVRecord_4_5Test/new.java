package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

class CSVRecord_4_5Test {

    @Test
    void testIsConsistent_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertEquals(true, record.isConsistent(), "Expected isConsistent to return true when mapping is null.");
    }

    @Test
    void testIsConsistent_mappingSizeEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertEquals(true, record.isConsistent(), "Expected isConsistent to return true when mapping size equals values length.");
    }

    @Test
    void testIsConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);

        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertEquals(false, record.isConsistent(), "Expected isConsistent to return false when mapping size does not equal values length.");
    }

    @Test
    void testIsConsistent_emptyValues() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{}, mapping, null, 1);
        Assertions.assertEquals(false, record.isConsistent(), "Expected isConsistent to return false when values are empty and mapping is not null.");
    }

    @Test
    void testIsConsistent_emptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertEquals(false, record.isConsistent(), "Expected isConsistent to return false when mapping is empty and values are not.");
    }
}