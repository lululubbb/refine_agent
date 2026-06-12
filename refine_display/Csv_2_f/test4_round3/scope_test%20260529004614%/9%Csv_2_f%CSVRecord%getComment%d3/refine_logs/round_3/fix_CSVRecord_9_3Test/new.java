package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_9_3Test {

    @Test
    public void testGetComment_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment(), "Expected comment does not match");
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment(), "Expected comment does not match for empty comment");
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment(), "Expected comment does not match for null comment");
    }

    @Test
    public void testGetComment_withSpecialCharacters() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "!@#$%^&*()_+";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment(), "Expected comment does not match for special characters");
    }

    @Test
    public void testGetComment_boundaryCase() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "A"; // boundary case with a single character
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment(), "Expected comment does not match for boundary case");
    }

    @Test
    public void testGetComment_longComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = new String(new char[1000]).replace("\0", "longComment"); // long comment
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment(), "Expected comment does not match for long comment");
    }
}