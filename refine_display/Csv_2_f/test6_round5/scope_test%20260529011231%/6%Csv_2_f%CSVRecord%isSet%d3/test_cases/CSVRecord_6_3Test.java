package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

public class CSVRecord_6_3Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() {
        mapping = new HashMap<>();
    }

    @Test
    public void testisSet_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        mapping.put("key1", 0);
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = csvRecord.isSet("key1");
        Assertions.assertEquals(true, result, "Expected key1 to be set but it was not.");
    }

    @Test
    public void testisSet_keyNotMapped() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = csvRecord.isSet("key2");
        Assertions.assertEquals(false, result, "Expected key2 to not be set as it is not mapped.");
    }

    @Test
    public void testisSet_indexOutOfBounds() throws Exception {
        String[] values = {"value1"};
        mapping.put("key1", 1);
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = csvRecord.isSet("key1");
        Assertions.assertEquals(false, result, "Expected key1 to be out of bounds and not set.");
    }

    @Test
    public void testisSet_emptyValuesArray() throws Exception {
        String[] values = {};
        mapping.put("key1", 0);
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = csvRecord.isSet("key1");
        Assertions.assertEquals(false, result, "Expected key1 to not be set since values array is empty.");
    }

    @Test
    public void testisSet_mappedButNotSet() throws Exception {
        String[] values = {"value1"};
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result1 = csvRecord.isSet("key1");
        boolean result2 = csvRecord.isSet("key2");
        Assertions.assertEquals(true, result1, "Expected key1 to be set.");
        Assertions.assertEquals(false, result2, "Expected key2 to not be set as it points to an index that does not exist.");
    }
}