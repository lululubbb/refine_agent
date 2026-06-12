package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_12_1Test {

    @Test
    public void testtoString_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = createMapping(values.length);
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        String result = invokeToString(csvRecord);
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testtoString_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = createMapping(values.length);
        String comment = null;
        long recordNumber = 2;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        String result = invokeToString(csvRecord);
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testtoString_singleElement() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = createMapping(values.length);
        String comment = "Single value comment";
        long recordNumber = 3;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        String result = invokeToString(csvRecord);
        Assertions.assertEquals("[singleValue]", result);
    }

    @Test
    public void testtoString_boundaryValues() throws Exception {
        String[] values = {null, "value2", "value3"};
        Map<String, Integer> mapping = createMapping(values.length);
        String comment = "Boundary values test";
        long recordNumber = 4;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        String result = invokeToString(csvRecord);
        Assertions.assertEquals("[null, value2, value3]", result);
    }

    private String invokeToString(CSVRecord csvRecord) throws Exception {
        return csvRecord.toString();
    }

    private Map<String, Integer> createMapping(int size) {
        Map<String, Integer> mapping = new HashMap<>();
        for (int i = 0; i < size; i++) {
            mapping.put("key" + (i + 1), i);
        }
        return mapping;
    }
}