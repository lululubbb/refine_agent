package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_6_1Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() {
        mapping = new HashMap<>();
    }

    @Test
    public void testisSet_nameMappedAndIndexInBounds() throws Exception {
        String name = "column1";
        mapping.put(name, 0);
        String[] values = {"value1"};
        csvRecord = new CSVRecord(values, mapping, null, 1);

        boolean result = csvRecord.isSet(name);

        Assertions.assertEquals(true, result, "Expected result to be true when name is mapped and index is in bounds.");
    }

    @Test
    public void testisSet_nameMappedAndIndexOutOfBounds() throws Exception {
        String name = "column1";
        mapping.put(name, 1);
        String[] values = {"value1"};
        csvRecord = new CSVRecord(values, mapping, null, 1);

        boolean result = csvRecord.isSet(name);

        Assertions.assertEquals(false, result, "Expected result to be false when name is mapped but index is out of bounds.");
    }

    @Test
    public void testisSet_nameNotMapped() throws Exception {
        String name = "column2";
        String[] values = {"value1"};
        csvRecord = new CSVRecord(values, mapping, null, 1);

        boolean result = csvRecord.isSet(name);

        Assertions.assertEquals(false, result, "Expected result to be false when name is not mapped.");
    }

    @Test
    public void testisSet_emptyMapping() throws Exception {
        String name = "column1";
        String[] values = {"value1"};
        csvRecord = new CSVRecord(values, mapping, null, 1);

        boolean result = csvRecord.isSet(name);

        Assertions.assertEquals(false, result, "Expected result to be false when mapping is empty.");
    }

    @Test
    public void testisSet_nullName() throws Exception {
        String name = null;
        String[] values = {"value1"};
        csvRecord = new CSVRecord(values, mapping, null, 1);

        boolean result = csvRecord.isSet(name);

        Assertions.assertEquals(false, result, "Expected result to be false when name is null.");
    }
}